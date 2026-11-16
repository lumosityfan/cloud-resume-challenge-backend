# Cloud Resume Challenge: Backend

The serverless backend for my resume website, **[jeffxieresumewebsite.com](https://www.jeffxieresumewebsite.com)**. Everything is defined as code with **Terraform** and deployed by **GitHub Actions**.

> The static site and its CI/CD live in **[cloud-resume-challenge](https://github.com/lumosityfan/cloud-resume-challenge)**.

## What it provides

| Endpoint / function | Purpose | Backed by |
|---|---|---|
| `GET /visitorCount` | Returns the current visitor count | Lambda, DynamoDB |
| `POST /visitorCount/increment` | Increments the total visitor count | Lambda, DynamoDB |
| `POST /uniqueVisitorCount/increment` | Counts each visitor once | Lambda, DynamoDB |
| `POST /resume-summarizer` | Summarizes an uploaded PDF resume | Lambda, Amazon Bedrock |
| `POST /job-match-calculator` | Scores a resume against a job description or posting URL (Ashby job boards supported) | Lambda, OpenAI API |

## Architecture

```
Browser ──► API Gateway (HTTP API) ──► Lambda (Python 3.13) ──► DynamoDB
                                                  ├──► Amazon Bedrock (resume summarizer)
                                                  └──► OpenAI API (job match calculator)
```

**Design notes**

- **Per-IP rate limiting:** a DynamoDB-backed fixed-window limiter (`src/rate_limiter.py`, default 5 requests/hour) protects the routes that call paid LLM APIs.
- **SSRF protection:** the job-match Lambda refuses non-HTTP(S) URLs and any URL that resolves to a private or internal address before fetching it.
- **CORS allow-list:** origins are controlled in `src/allowed_origins.py`.
- **Least-privilege IAM:** each Lambda has its own role scoped to the tables and Bedrock resources it needs.
- **Reproducible builds:** the job-match Lambda is packaged with `terraform-aws-modules/lambda` using `build_in_docker`, so compiled dependencies match the Lambda runtime.
- **Drift detection:** a scheduled GitHub Actions workflow runs `terraform plan -detailed-exitcode` daily and flags infrastructure that has changed outside of code.

## CI/CD

| Workflow | What it does |
|---|---|
| `terraform.yml` | `init`, `fmt -check` and `plan` on every push and PR; `apply` on push to `main` |
| `drift-detection.yml` | Daily `terraform plan` to detect configuration drift |

## Repository layout

```
.
├── main.tf            # Lambdas, API Gateway, DynamoDB tables, IAM, S3 artifact bucket
├── variables.tf       # aws_region, openai_api_key (sensitive)
├── outputs.tf
├── terraform.tf       # providers and backend
└── src/
    ├── get_visitor_counter.py
    ├── post_visitor_counter_increment.py
    ├── post_unique_visitor_counter_increment.py
    ├── resume_summarizer.py
    ├── job_match_calculator.py
    ├── rate_limiter.py
    ├── allowed_origins.py
    └── requirements.txt
```

## Deploying your own

**Prerequisites:** Terraform 1.x, Docker (for the Lambda build), AWS credentials, and an OpenAI API key.

```bash
git clone https://github.com/lumosityfan/cloud-resume-challenge-backend.git
cd cloud-resume-challenge-backend

export AWS_REGION=us-east-2
export TF_VAR_openai_api_key="your-key-here"

terraform init
terraform plan
terraform apply
```

You will also need to adjust the allowed origins in `src/allowed_origins.py` and enable access to the Bedrock model used by the resume summarizer in your AWS account.

## Tech stack

Terraform · AWS Lambda · API Gateway · DynamoDB · Amazon Bedrock · IAM · CloudWatch · Python 3.13 · GitHub Actions
