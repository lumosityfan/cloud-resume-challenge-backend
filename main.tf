provider "aws" {
    region = "us-east-1"
}

resource "random_pet" "lambda_bucket_name" {
    prefix = "cloud-resume-challenge"
    length = 4
}

resource "aws_s3_bucket" "lambda_bucket" {
    bucket = random_pet.lambda_bucket_name
}

resource "aws_s3_bucket_ownership_controls" "lambda_bucket" {
    bucket = aws_s3_bucket.lambda_bucket.id
    rule {
        object_ownership = "BucketOwnerPreferred"
    }
}

resource "aws_s3_bucket_acl" "lambda_bucket" {
    depends_on [aws_s3_bucket_ownership_controls.lambda_bucket]

    bucket = aws_s3_bucket.lambda_bucket.id
    acl    = "private"
}