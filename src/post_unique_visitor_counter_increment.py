import json
import boto3
import sys
import base64
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta, timezone

dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
unique_visitor_counter_table = dynamodb.Table('unique-visitor-counter')
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
        if event['routeKey'] == "POST /uniqueVisitorCount/increment":
            # Get ip address
            ip_address = event['requestContext']['http']['sourceIp']
            ip_hash = hashlib.md5(ip_address.encode()).hexdigest()

            # Check if the IP address already exists in the unique visitor counter table
            unique_visitor_response = unique_visitor_counter_table.get_item(Key={'ip_address': ip_hash})
            if 'Item' not in unique_visitor_response:
                # If the IP address is not found, increment the unique visitor counter
                unique_visitor_counter_table.put_item(Item={
                    'ip_address': ip_hash,
                    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
                })
                visitor_counter_table.update_item(
                    Key={'id': 'unique-visitor-counter', 'name': 'Unique Visitor Counter'},
                    UpdateExpression='SET counter = if_not_exists(counter, :start) + :inc',
                ExpressionAttributeValues={
                        ':inc': Decimal(1),
                        ':start': Decimal(0)
                    }
                )
            else:
                # Check to see if the time since the last visit from this IP address is greater than a certain threshold (e.g., 30 minutes)
                # If it is, we can consider this a new unique visit and increment the counter again
                # For simplicity, this example does not implement the time-based logic, but it can be added by storing a timestamp in the unique visitor counter table and comparing it to the current time before deciding to increment the counter again
                time = datetime.now(timezone.utc) - datetime.strptime(unique_visitor_response['Item']['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                if time > timedelta(minutes=10080):
                    unique_visitor_counter_table.put_item(Item={
                        'ip_address': ip_hash,
                        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
                    })
                    visitor_counter_table.update_item(
                        Key={'id': 'unique-visitor-counter'},
                        UpdateExpression='SET counter = if_not_exists(counter, :start) + :inc',
                        ExpressionAttributeValues={
                            ':inc': Decimal(1),
                            ':start': Decimal(0)
                        }
                    )
            unique_visitor_counter_total = unique_visitor_counter_table.scan(Select='COUNT')['Count']
            body = {'unique_visitor_counter': unique_visitor_counter_total}
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