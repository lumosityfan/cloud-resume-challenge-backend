provider "aws" {
    region = "us-east-2"
}

data "archive_file" "lambda_function" {
    type = "zip"

    source_dir  = "${path.module}/src"
    output_path = "${path.module}/lambda_function.zip"
}

resource "random_pet" "lambda_bucket_name" {
    prefix = "cloud-resume-challenge"
    length = 4
}

resource "aws_s3_bucket" "lambda_bucket" {
    bucket = random_pet.lambda_bucket_name.id
}

resource "aws_s3_bucket_ownership_controls" "lambda_bucket" {
    bucket = aws_s3_bucket.lambda_bucket.id
    rule {
        object_ownership = "BucketOwnerPreferred"
    }
}

resource "aws_s3_bucket_acl" "lambda_bucket" {
    depends_on = [aws_s3_bucket_ownership_controls.lambda_bucket]

    bucket = aws_s3_bucket.lambda_bucket.id
    acl    = "private"
}

resource "aws_s3_object" "lambda_function" {
    bucket = aws_s3_bucket.lambda_bucket.id

    key = "lambda_function.zip"
    source = data.archive_file.lambda_function.output_path
    etag = filemd5(data.archive_file.lambda_function.output_path)
}

resource "aws_lambda_function" "lambda_function" {
    function_name = "cloud-resume-challenge"

    s3_bucket = aws_s3_bucket.lambda_bucket.id
    s3_key    = aws_s3_object.lambda_function.key

    runtime = "python3.13"
    handler = "lambda_function.lambda_handler"

    source_code_hash = data.archive_file.lambda_function.output_base64sha256

    role = aws_iam_role.lambda_exec.arn 
}

resource "aws_cloudwatch_log_group" "lambda_function" {
    name = "/aws/lambda/${aws_lambda_function.lambda_function.function_name}"

    retention_in_days = 30
} 

resource "aws_iam_role" "lambda_exec" {
    name = "lambda_function"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [{
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Sid    = ""
            Principal = {
                Service = "lambda.amazonaws.com"
            }
        }]
    })
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
    role = aws_iam_role.lambda_exec.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_apigatewayv2_api" "lambda" {
    name = "cloud-resume-challenge"
    protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "lambda" {
  api_id = aws_apigatewayv2_api.lambda.id

  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

resource "aws_apigatewayv2_integration" "lambda_function" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri    = aws_lambda_function.lambda_function.invoke_arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "lambda_function_get_visitor_counter" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "GET /visitor-counter"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_function.id}"
}

resource "aws_apigatewayv2_route" "lambda_function_post_resume_summarizer" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "POST /resume-summarizer"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_function.id}"
}

resource "aws_apigatewayv2_route" "lambda_function_options_resume_summarizer" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "OPTIONS /resume-summarizer"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_function.id}"
}

resource "aws_apigatewayv2_route" "lambda_function_get_id" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "GET /{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_function.id}"
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.lambda.name}"

  retention_in_days = 30
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

resource "aws_dynamodb_table" "cloud-resume-challenge" {
  name           = "cloud-resume-challenge"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "counter"
    type = "N"
  }

  attribute {
    name = "name"
    type = "S"
  }

  ttl {
    attribute_name = "TimeToExist"
    enabled        = true
  }

  global_secondary_index {
    name               = "CounterIndex"
    hash_key           = "name"
    range_key          = "counter"
    write_capacity     = 10
    read_capacity      = 10
    projection_type    = "INCLUDE"
    non_key_attributes = ["id"]
  }

  tags = {
    Name        = "dynamodb-table-1"
    Environment = "production"
  }
}
