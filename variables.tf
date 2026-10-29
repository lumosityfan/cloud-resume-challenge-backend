variable "openai_api_key" {
  description = "OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}