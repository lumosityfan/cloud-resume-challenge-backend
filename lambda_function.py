import json
import boto3
from decimal import Decimal

client = boto3.client('dynamodb')
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table('cloud-resume-challenge')
tableName = 'cloud-resume-challenge'


def lambda_handler(event, context):
    print(event)
    body = {}
    statusCode = 200
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # if event['routeKey'] == "DELETE /{id}":
        #     table.delete_item(
        #         Key={'id': event['pathParameters']['id']})
        #     body = 'Deleted item ' + event['pathParameters']['id']
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
    except KeyError:
        statusCode = 400
        body = 'Unsupported route: ' + event['routeKey']
    body = json.dumps(body)
    res = {
        "statusCode": statusCode,
        "headers": {
            "Content-Type": "application/json",
            'Access-Control-Allow-Origin': 'http://jeffxieresumewebsite.com.s3-website.us-east-2.amazonaws.com',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        },
        "body": body
    }
    return res