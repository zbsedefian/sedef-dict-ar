# Environment Variables for the Application
variable "open_api_key" {
  description = "Open API Key for the Arabic dictionary app"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}