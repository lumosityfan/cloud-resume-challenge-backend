import json
import boto3
import sys
import base64
from decimal import Decimal

dynamodb_client = boto3.client('dynamodb')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-2')
dynamodb = boto3.resource("dynamodb")
visitor_counter_table = dynamodb.Table('cloud-resume-challenge')
tableName = 'cloud-resume-challenge'
human_or_bot_table = dynamodb.Table('human-or-bot')


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
        if event['routeKey'] == "GET /visitor-counter":
            event_data = {
                'ip_address': event['requestContext']['http']['sourceIp'],
                'user_agent': event['requestContext']['http']['userAgent'],
                'referer': event['headers'].get('referer', ''),
                'timestamp': event['requestContext']['time']
            }
            bedrock_response = bedrock_client.invoke_model(
                modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': f'''Given the following visitor data in JSON format, classify if the user is real or bot-like, and rate intent to bounce. Here's the visitor data: {json.dumps(event_data)}'''
                            }
                        ]
                    }],
                    'max_tokens': 256
                })
            )
            bedrock_body = json.loads(bedrock_response['body'].read())
            if "REAL USER" in bedrock_body['content'][0]['text']:
                event_data["traffic_type"] = "likely human"
                visitor_counter_response = visitor_counter_table.update_item(
                    Key={'id': 'visitor-counter'},
                    UpdateExpression='ADD #c :inc SET #n = if_not_exists(#n, :name)',
                    ExpressionAttributeNames={
                        '#c': 'counter',
                        '#n': 'name'
                    },
                    ExpressionAttributeValues={
                        ':inc': Decimal('1'),
                        ':name': 'Visitor Counter'
                    },
                    ReturnValues='ALL_NEW'
                )
            elif "BOT-LIKE" in bedrock_body['content'][0]['text']:
                event_data["traffic_type"] = "likely bot"
                visitor_counter_response = visitor_counter_table.get_item(Key={'id': 'visitor-counter'})
            human_or_bot_table.put_item(Item={
                    "ip_address": hash(event_data['ip_address']),
                    "user_agent": event_data['user_agent'],
                    "referer": event_data['referer'],
                    "timestamp": event_data['timestamp'],
                    "traffic_type": event_data['traffic_type']
            })
            item = visitor_counter_response['Attributes']
            body = [{'counter': float(item['counter']), 'id': item['id'], 'name': item['name']}]
        elif event['routeKey'] == "POST /visitor-counter":
            requestJSON = json.loads(event['body'])
            visitor_counter_table.put_item(
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