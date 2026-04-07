import json
import boto3
import sys
import base64
from decimal import Decimal

dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
visitor_counter_table = dynamodb.Table('visitor-counter')
human_or_bot_table = dynamodb.Table('human-or-bot')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-2')

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
        if event['routeKey'] == "POST /visitorCount/increment":
            requestJSON = json.loads(event['body'])
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
                requestJSON['counter'] = requestJSON['counter'] + 1
                visitor_counter_table.put_item(
                    Item={
                        'id': requestJSON['id'],
                        'counter': requestJSON['counter'],
                        'name': requestJSON['name']
                    })
            elif "BOT-LIKE" in bedrock_body['content'][0]['text']:
                event_data["traffic_type"] = "likely bot"
            else:
                event_data["traffic_type"] = "inconclusive"
            human_or_bot_table.put_item(Item={
                "ip_address": hash(event_data['ip_address']),
                "user_agent": event_data['user_agent'],
                "referer": event_data['referer'],
                "timestamp": event_data['timestamp'],
                "traffic_type": event_data['traffic_type']
            })
            body = [{'counter': float(requestJSON['counter']), 'id': requestJSON['id'], 'name': requestJSON['name']}]
    except Exception as e:
        statusCode = 500
        body = {'error': str(e)}
    except KeyError as e:
        statusCode = 400
        body = {'error': f'Unsupported route: {str(e)}'}
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": headers,
        "body": body
    }
    return res