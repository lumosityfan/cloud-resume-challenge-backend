terraform {
  backend "s3" {
    bucket       = "cloud-resume-challenge-backend-tfstate"
    key          = "cloud-resume-backend/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.1"
    }
  }

  required_version = "~> 1.2"
}