import os
import json
import io
import base64
from openai import OpenAI
from pypdf import PdfReader
import docx2txt
import requests
from bs4 import BeautifulSoup

client = OpenAI()


class Uploaded:
    """Small wrapper so a base64 payload behaves like the file-like
    object extract_text() expects (needs .filename plus standard
    file methods — PdfReader needs .seek()/.tell() too, not just .read())."""
    def __init__(self, filename, raw_bytes):
        self.filename = filename
        self._buf = io.BytesIO(raw_bytes)

    def read(self, *args, **kwargs):
        return self._buf.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._buf.seek(*args, **kwargs)

    def tell(self):
        return self._buf.tell()


def extract_text(uploaded_file):
    filename = uploaded_file.filename.lower()

    if filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif filename.endswith(".docx"):
        file_bytes = io.BytesIO(uploaded_file.read())
        return docx2txt.process(file_bytes)

    elif filename.endswith(".doc"):
        return None

    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")


import re
from urllib.parse import urlparse


def extract_ashby_job_text(url):
    """Ashby job pages are client-side rendered — the raw HTML only
    contains the title. Use Ashby's public job-board API instead."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]

    if len(path_parts) < 1:
        return None, None  # not a recognizable Ashby URL, fall back

    company_slug = path_parts[0]
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"

    try:
        resp = requests.get(api_url, params={"includeCompensation": "false"}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, f"Error fetching job data from Ashby: {e}"

    data = resp.json()
    jobs = data.get("jobs", [])

    # Match by jobId (last path segment) first, fall back to exact jobUrl match
    job_id = path_parts[-1] if len(path_parts) > 1 else None
    match = None
    for job in jobs:
        job_url_parts = [p for p in urlparse(job.get("jobUrl", "")).path.split("/") if p]
        if job_id and job_url_parts and job_url_parts[-1] == job_id:
            match = job
            break
        if job.get("jobUrl", "").rstrip("/") == url.rstrip("/"):
            match = job
            break

    if not match:
        return None, "Couldn't find that specific job posting on the company's Ashby board (it may be unlisted or expired)."

    description = match.get("descriptionPlain")
    if not description:
        html_desc = match.get("descriptionHtml", "")
        description = BeautifulSoup(html_desc, "html.parser").get_text(separator="\n")

    title = match.get("title", "")
    full_text = f"{title}\n\n{description}".strip()

    if len(full_text) < 100:
        return None, "The extracted job posting is too short to be a valid job description."

    return full_text, None


def extract_job_text_from_url(url):
    if "jobs.ashbyhq.com" in urlparse(url).netloc:
        text, error = extract_ashby_job_text(url)
        if text is not None:
            return text, None
        if error:
            return None, error
        # fall through to generic scraping if Ashby-specific extraction
        # didn't apply (e.g. malformed URL)

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, f"Error fetching the URL: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) < 100:
        return None, "The extracted text is too short to be a valid job description."

    return cleaned, None


def lambda_handler(event, context):
    origin = event.get('headers', {}).get('origin', '')

    allowed_origins = [
        'http://localhost:3000',
        'http://localhost:5500',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://127.0.0.1:5500',
        'http://www.jeffxieresumewebsite.com',
        'http://jeffxieresumewebsite.com',
        'http://jeffxieresumewebsite.com.s3-website.us-east-2.amazonaws.com',
    ]

    cors_origin = origin if origin in allowed_origins else '*'
    headers = {
        "Content-Type": "application/json",
        'Access-Control-Allow-Origin': cors_origin,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    }

    # Handle CORS preflight explicitly — this is the request that was
    # falling through and crashing before.
    if event.get('routeKey') == "OPTIONS /job-match-calculator":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    statusCode = 200
    body = {}

    try:
        if event['routeKey'] == "POST /job-match-calculator":
            request_body = json.loads(event['body'])
            job_description = request_body.get("jobDescription")
            job_url = request_body.get("jobUrl")
            pdf_base64 = request_body.get("pdfBase64")
            pdf_filename = request_body.get("pdfFilename", "resume.pdf")

            if not pdf_base64:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Please upload a resume file"})
                }

            if job_url:
                job_description, error = extract_job_text_from_url(job_url)
                if error:
                    return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": error})}
            elif not job_description:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Please provide either a job description or a job URL"})
                }

            # Decode the base64 payload (strip a data URL prefix if present)
            if "," in pdf_base64 and pdf_base64.strip().startswith("data:"):
                pdf_base64 = pdf_base64.split(",", 1)[1]
            raw_bytes = base64.b64decode(pdf_base64)
            uploaded_file = Uploaded(pdf_filename, raw_bytes)

            resume_text = extract_text(uploaded_file)

            if resume_text is None:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Legacy .doc files aren't supported - please upload a .pdf or .docx file"})
                }

            if not resume_text.strip():
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Couldn't extract any text from the resume"})
                }

            prompt = f"""You are a career advisor. Compare the following resume against the job description and provide:

Respond ONLY with valid JSON (no markdown fences, no preamble) in exactly this shape:
{{
"score": <integer 0-100>,
"summary": "<one sentence overall verdict>",
"strengths": ["<strength 1>", "<strength 2>", "..."],
"gaps": ["<gap 1>", "<gap 2>", "..."],
"suggestions": ["<suggestion 1>", "<suggestion 2>", "..."]
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            body = json.loads(response.choices[0].message.content)
        else:
            statusCode = 404
            body = {"error": f"No handler for route {event.get('routeKey')}"}

    except Exception as e:
        statusCode = 500
        body = {"error": "Error processing the request: " + str(e)}

    return {
        "statusCode": statusCode,
        "headers": headers,
        "body": json.dumps(body)
    }