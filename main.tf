# AWS provider
provider "aws" {
  region = "us-east-2"
}

# Archive files
data "archive_file" "resume_summarizer" {
  type = "zip"

  source_dir  = "${path.module}/src"
  output_path = "${path.module}/resume_summarizer.zip"
}

data "archive_file" "get_visitor_counter" {
  type = "zip"

  source_dir  = "${path.module}/src"
  output_path = "${path.module}/get_visitor_counter.zip"
}

data "archive_file" "post_visitor_counter_increment" {
  type = "zip"

  source_dir  = "${path.module}/src"
  output_path = "${path.module}/post_visitor_counter_increment.zip"
}

data "archive_file" "post_unique_visitor_counter_increment" {
  type = "zip"

  source_dir  = "${path.module}/src"
  output_path = "${path.module}/post_unique_visitor_counter_increment.zip"
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

resource "aws_s3_object" "resume_summarizer" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "resume_summarizer.zip"
  source = data.archive_file.resume_summarizer.output_path
  etag   = filemd5(data.archive_file.resume_summarizer.output_path)
}

resource "aws_s3_object" "get_visitor_counter" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "get_visitor_counter.zip"
  source = data.archive_file.get_visitor_counter.output_path
  etag   = filemd5(data.archive_file.get_visitor_counter.output_path)
}

resource "aws_s3_object" "post_visitor_counter_increment" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "post_visitor_counter_increment.zip"
  source = data.archive_file.post_visitor_counter_increment.output_path
  etag   = filemd5(data.archive_file.post_visitor_counter_increment.output_path)
}

resource "aws_s3_object" "post_unique_visitor_counter_increment" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "post_unique_visitor_counter_increment.zip"
  source = data.archive_file.post_unique_visitor_counter_increment.output_path
  etag   = filemd5(data.archive_file.post_unique_visitor_counter_increment.output_path)
}

resource "aws_lambda_function" "resume_summarizer" {
  function_name = "resume-summarizer"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_object.resume_summarizer.key

  runtime = "python3.13"
  handler = "resume_summarizer.lambda_handler"

  source_code_hash = data.archive_file.resume_summarizer.output_base64sha256

  role    = aws_iam_role.lambda_exec.arn
  timeout = 30
}

resource "aws_cloudwatch_log_group" "resume_summarizer" {
  name = "/aws/lambda/${aws_lambda_function.resume_summarizer.function_name}"

  retention_in_days = 30
}

resource "aws_lambda_function" "get_visitor_counter" {
  function_name = "get_visitor_counter"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_object.get_visitor_counter.key

  runtime = "python3.13"
  handler = "get_visitor_counter.lambda_handler"

  source_code_hash = data.archive_file.get_visitor_counter.output_base64sha256

  role    = aws_iam_role.lambda_get_role.arn
  timeout = 30
}

resource "aws_cloudwatch_log_group" "get_visitor_counter" {
  name = "/aws/lambda/${aws_lambda_function.get_visitor_counter.function_name}"

  retention_in_days = 30
}

resource "aws_lambda_function" "post_visitor_counter_increment" {
  function_name = "post_visitor_counter_increment"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_object.post_visitor_counter_increment.key

  runtime = "python3.13"
  handler = "post_visitor_counter_increment.lambda_handler"

  source_code_hash = data.archive_file.post_visitor_counter_increment.output_base64sha256

  role    = aws_iam_role.lambda_post_role.arn
  timeout = 30
}

resource "aws_cloudwatch_log_group" "post_visitor_counter_increment" {
  name = "/aws/lambda/${aws_lambda_function.post_visitor_counter_increment.function_name}"

  retention_in_days = 30
}

resource "aws_lambda_function" "post_unique_visitor_counter_increment" {
  function_name = "post_unique_visitor_counter_increment"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_object.post_unique_visitor_counter_increment.key

  runtime = "python3.13"
  handler = "post_unique_visitor_counter_increment.lambda_handler"

  source_code_hash = data.archive_file.post_unique_visitor_counter_increment.output_base64sha256

  role    = aws_iam_role.lambda_exec.arn
  timeout = 30
}

resource "aws_cloudwatch_log_group" "post_unique_visitor_counter_increment" {
  name = "/aws/lambda/${aws_lambda_function.post_unique_visitor_counter_increment.function_name}"

  retention_in_days = 30
}

# AWS IAM Roles
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

resource "aws_iam_role" "lambda_get_role" {
  name = "lambda_get_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "lambda_post_role" {
  name = "lambda_post_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# AWS IAM Role Policies
resource "aws_iam_role_policy" "bedrock_inference_profile_lambda_exec" {
  name = "bedrock-inference-profile-lambda_exec"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:us-east-2::foundation-model/*",
          "arn:aws:bedrock:*:533266979920:inference-profile/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_inference_profile_lambda_post_role" {
  name = "bedrock-inference-profile-lambda-post-role"
  role = aws_iam_role.lambda_post_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:us-east-2::foundation-model/*",
          "arn:aws:bedrock:*:533266979920:inference-profile/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "get_policy" {
  name = "get_read_only_policy"
  role = aws_iam_role.lambda_get_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = aws_dynamodb_table.visitor_counter.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "post_policy" {
  name = "post_write_only_policy"
  role = aws_iam_role.lambda_post_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.visitor_counter.arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = aws_dynamodb_table.human_or_bot.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "get_basic_execution" {
  role       = aws_iam_role.lambda_get_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "post_basic_execution" {
  role       = aws_iam_role.lambda_post_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "bedrock_policy_lambda_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_iam_role_policy_attachment" "bedrock_policy_lambda_post_role" {
  role       = aws_iam_role.lambda_post_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_apigatewayv2_api" "lambda" {
  name          = "cloud-resume-challenge"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [
      "https://www.jeffxieresumewebsite.com",
      "https://jeffxieresumewebsite.com",
      "http://localhost:3000",
      "http://localhost:5500",
      "http://localhost:8000",
      "http://127.0.0.1:8000",
      "http://127.0.0.1:5500"
    ]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 300
  }
}

resource "aws_iam_role" "api_gw_cloudwatch" {
  name = "api-gw-cloudwatch"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "unique_visitor_dynamodb_policy" {
  name = "unique_visitor_dynamodb_policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.unique_visitor_counter.arn,
          aws_dynamodb_table.visitor_counter.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_gw_cloudwatch" {
  role       = aws_iam_role.api_gw_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gw_cloudwatch.arn
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

# API Gateway integrations
resource "aws_apigatewayv2_integration" "resume_summarizer" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri        = aws_lambda_function.resume_summarizer.invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_visitor_counter" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri        = aws_lambda_function.get_visitor_counter.invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "post_visitor_counter_increment" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri        = aws_lambda_function.post_visitor_counter_increment.invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "post_unique_visitor_counter_increment" {
  api_id = aws_apigatewayv2_api.lambda.id

  integration_uri        = aws_lambda_function.post_unique_visitor_counter_increment.invoke_arn
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# API Gateway routes
resource "aws_apigatewayv2_route" "get_visitor_counter" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "GET /visitorCount"
  target    = "integrations/${aws_apigatewayv2_integration.get_visitor_counter.id}"
}

resource "aws_apigatewayv2_route" "post_visitor_counter_increment" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "POST /visitorCount/increment"
  target    = "integrations/${aws_apigatewayv2_integration.post_visitor_counter_increment.id}"
}

resource "aws_apigatewayv2_route" "post_unique_visitor_counter_increment" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "POST /uniqueVisitorCount/increment"
  target    = "integrations/${aws_apigatewayv2_integration.post_unique_visitor_counter_increment.id}"
}

resource "aws_apigatewayv2_route" "post_resume_summarizer" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "POST /resume-summarizer"
  target    = "integrations/${aws_apigatewayv2_integration.resume_summarizer.id}"
}

resource "aws_apigatewayv2_route" "options_resume_summarizer" {
  api_id = aws_apigatewayv2_api.lambda.id

  route_key = "OPTIONS /resume-summarizer"
  target    = "integrations/${aws_apigatewayv2_integration.resume_summarizer.id}"
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.lambda.name}"

  retention_in_days = 30
}

resource "aws_lambda_permission" "api_gw_resume_summarizer" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.resume_summarizer.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_get_visitor_counter" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_visitor_counter.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_post_visitor_counter_increment" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_visitor_counter_increment.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_post_unique_visitor_counter_increment" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_unique_visitor_counter_increment.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn    = "${aws_apigatewayv2_api.lambda.execution_arn}/*/*"
}

resource "aws_dynamodb_table" "visitor_counter" {
  name           = "visitor-counter"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "TimeToExist"
    enabled        = true
  }

  tags = {
    Name        = "cloud-resume-challenge"
    Environment = "production"
  }
}

resource "aws_dynamodb_table" "human_or_bot" {
  name           = "human-or-bot"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "ip_address"

  attribute {
    name = "ip_address"
    type = "N"
  }

  ttl {
    attribute_name = "TimeToExist"
    enabled        = true
  }

  tags = {
    Name        = "cloud-resume-challenge"
    Environment = "production"
  }
}

resource "aws_dynamodb_table" "unique_visitor_counter" {
  name           = "unique-visitor-counter"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "ip_address"

  attribute {
    name = "ip_address"
    type = "S"
  }

  ttl {
    attribute_name = "TimeToexist"
    enabled        = true
  }

  tags = {
    Name        = "cloud-resume-challenge"
    Environment = "production"
  }
}