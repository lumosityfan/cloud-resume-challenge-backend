import json
import boto3
import sys
import base64
from decimal import Decimal

dynamodb_client = boto3.client('dynamodb')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-2')
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('cloud-resume-challenge')
tableName = 'cloud-resume-challenge'


def lambda_handler(event, context):
    # get the request origin
    origin = event.get('headers', {}).get('origin', '')

    # allowlist of valid origins
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
        print("EVENT:", json.dumps(event))
        if event['routeKey'] == "GET /{id}":
            body = table.get_item(
                Key={'id': event['pathParameters']['id']})
            body = body["Item"]
            responseBody = [
                {'counter': float(body['counter']), 'id': body['id'], 'name': body['name']}]
            body = responseBody
        elif event['routeKey'] == "GET /":
            body = table.scan()
            body = body["Items"]
            print("ITEMS----")
            print(body)
            responseBody = []
            for items in body:
                responseItems = [
                    {'counter': float(items['counter']), 'id': items['id'], 'name': items['name']}]
                responseBody.append(responseItems)
            body = responseBody
        elif event['routeKey'] == "POST /":
            requestJSON = json.loads(event['body'])
            table.put_item(
                Item={
                    'id': requestJSON['id'],
                    'counter': requestJSON['counter'],
                    'name': requestJSON['name']
                })
            body = 'Put item ' + requestJSON['id']
        elif event['routeKey'] == "POST /resume-summarizer":
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
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": headers,
        "body": body
    }
    return res