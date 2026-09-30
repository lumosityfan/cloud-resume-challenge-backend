import os
import time

import boto3
from botocore.exceptions import ClientError

_dynamodb = boto3.resource("dynamodb")

RATE_LIMIT_TABLE = os.environ.get("RATE_LIMIT_TABLE", "rate-limiter")
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "5"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "3600"))

def _client_ip(event):
    return event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown")

def check_rate_limit(event, route_name, max_requests=None, window_seconds=None):
    max_requests = max_requests if max_requests is not None else RATE_LIMIT_MAX_REQUESTS
    window_seconds = window_seconds if window_seconds is not None else RATE_LIMIT_WINDOW_SECONDS

    ip = _client_ip(event)
    now = int(time.time())
    window_start = now - (now % window_seconds)
    rate_key = f"{route_name}#{ip}#{window_start}"
    expire_at = window_start + window_seconds + 60 

    table = _dynamodb.Table(RATE_LIMIT_TABLE)

    try:
        table.update_item(
            Key={"rate_key": rate_key},
            UpdateExpression=(
                "SET request_count = if_not_exists(request_count, :zero) + :one, "
                "expire_at = :expire_at"
            ),
            ConditionExpression=(
                "attribute_not_exists(request_count) OR request_count < :limit"
            ),
            ExpressionAttributeValues={
                ":zero": 0,
                ":one": 1,
                ":limit": max_requests,
                ":expire_at": expire_at,
            },
        )
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        print(f"rate_limiter: DynamoDB error, failing open: {e}", flush=True)
        return True

def rate_limit_response(headers):
    import json

    return {
        "statusCode": 429,
        "headers": headers,
        "body": json.dumps({
            "error": "You've hit the rate limit for this feature. Please try again in a bit."
        }),
    }