import json
import boto3
import sys
import base64
import traceback
from decimal import Decimal
from allowed_origins import allowed_origins

from rate_limiter import check_rate_limit, rate_limit_response, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-2')

def lambda_handler(event, context):
    # get the request origin
    origin = event.get('headers', {}).get('origin', '')

    # temporary: allow all origins while testing locally
    cors_origin = origin if origin in allowed_origins else '*'
    body = {}
    statusCode = 200
    headers = {
        "Content-Type": "application/json",
        'Access-Control-Allow-Origin': cors_origin,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    }

    try:
        if event['routeKey'] == "POST /resume-summarizer":
            if not check_rate_limit(
                event,
                "resume-summarizer",
                max_requests=RATE_LIMIT_MAX_REQUESTS,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            ):
                return rate_limit_response(headers)
            
            request_body = json.loads(event['body'])
            pdf_base64 = request_body['pdfBase64']  # frontend sends base64-encoded PDF
    
            response = bedrock_client.invoke_model(
                modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {
                                'type': 'document',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'application/pdf',
                                    'data': pdf_base64
                                }
                            },
                            {
                                'type': 'text',
                                'text': '''Please summarize this resume in HTML format. 
                                Use the following structure:
                                - A <h3> tag for the candidate name
                                - A <p> tag for a 2-3 sentence professional summary
                                - A <h4>Key Skills</h4> followed by a <ul> with <li> items
                                - A <h4>Experience</h4> followed by a <ul> with <li> items for each role
                                - A <h4>Education</h4> followed by a <ul> with <li> items

                                Return only the HTML, no markdown, no code fences, no explanation. Remove the outer quotation marks and the html at the beginning.'''
                            }
                        ]
                    }],
                    'max_tokens': 1024
                })
            )
            bedrock_body = json.loads(response['body'].read())
            body = bedrock_body['content'][0]['text']
            print("body extracted:", body[:100], flush=True)
        elif event['routeKey'] == "OPTIONS /resume-summarizer":
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
    except KeyError as e:
        statusCode = 400
        body = 'Unsupported route: ' + str(e)
    except Exception as e:
        print(traceback.format_exc())
        statusCode = 500
        body = {'error': str(e)}
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": headers,
        "body": body
    }
    return res