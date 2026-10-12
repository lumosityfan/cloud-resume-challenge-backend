import json
import boto3
import sys
import base64
import hashlib
from decimal import Decimal
from allowed_origins import allowed_origins

from rate_limiter import check_rate_limit, rate_limit_response, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
visitor_counter_table = dynamodb.Table('visitor-counter')
human_or_bot_table = dynamodb.Table('human-or-bot')
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
        'Access-Control-Allow-Headers': 'Content-Type, Cache-Control',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    }

    try:
        if event['routeKey'] == "POST /visitorCount/increment":
            if not check_rate_limit(
                event,
                "post-visitor-counter-increment",
                max_requests=RATE_LIMIT_MAX_REQUESTS,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            ):
                return rate_limit_response(headers)
            
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
                                'text': f'''Given the following visitor data in JSON format, classify if the user is real or bot-like, and rate intent to bounce.  Reply with exactly REAL USER or BOT-LIKE. Here's the visitor data: {json.dumps(event_data)}'''
                            }
                        ]
                    }],
                    'max_tokens': 256
                })
            )
            bedrock_body = json.loads(bedrock_response['body'].read())
            if "REAL USER" in bedrock_body['content'][0]['text']:
                event_data["traffic_type"] = "likely human"
                visitor_counter_table.update_item(
                    Key={'id': 'visitor-counter'},
                    UpdateExpression='SET counter = if_not_exists(counter, :start) + :inc, name = :name',
                    ExpressionAttributeValues={
                        ':name': 'Visitor Counter',
                        ':inc': Decimal(1),
                        ':start': Decimal(0)
                    }
                )
                # requestJSON['counter'] = requestJSON['counter'] + 1
                # visitor_counter_table.put_item(
                #     Item={
                #         'id': requestJSON['id'],
                #         'counter': requestJSON['counter'],
                #         'name': requestJSON['name']
                #     })
            elif "BOT-LIKE" in bedrock_body['content'][0]['text']:
                event_data["traffic_type"] = "likely bot"
            else:
                event_data["traffic_type"] = "inconclusive"
            human_or_bot_table.put_item(Item={
                "ip_address": hashlib.md5(event_data["ip_address"].encode()).hexdigest(),
                "user_agent": event_data['user_agent'],
                "referer": event_data['referer'],
                "timestamp": event_data['timestamp'],
                "traffic_type": event_data['traffic_type']
            })
            body = [{'counter': float(requestJSON['counter']), 'id': requestJSON['id'], 'name': requestJSON['name']}]
    except KeyError as e:
        statusCode = 400
        body = {'error': f'Unsupported route: {str(e)}'}
    except Exception as e:
        statusCode = 500
        body = {'error': str(e)}
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": headers,
        "body": body
    }
    return res