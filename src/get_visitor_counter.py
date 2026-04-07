import json
import boto3
import sys
import base64
from decimal import Decimal

dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
visitor_counter_table = dynamodb.Table('visitor-counter')

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
        if event['routeKey'] == "GET /visitorCount":
            visitor_counter_response = visitor_counter_table.get_item(Key={'id': 'visitor-counter'})
            if not visitor_counter_response.get('Item'):
                visitor_counter_table.put_item(Item={'id': 'visitor-counter', 'counter': Decimal('0'), 'name': 'Visitor Counter'})
                visitor_counter_response = visitor_counter_table.get_item(Key={'id': 'visitor-counter'})
            item = visitor_counter_response['Item']
            body = [{'counter': float(item['counter']), 'id': item['id'], 'name': item['name']}]
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