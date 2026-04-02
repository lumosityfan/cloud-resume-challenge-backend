terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 6.17.0"
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