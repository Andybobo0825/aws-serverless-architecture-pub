variable "aws_region" {
  type        = string
  description = "Primary AWS region for regional MVP resources."
  default     = "ap-northeast-1"
}

variable "project_name" {
  type        = string
  description = "Project/name prefix."
  default     = "magic"
}

variable "environment" {
  type        = string
  description = "Environment label."
  default     = "mvp"
}

variable "app_domain_name" {
  type        = string
  description = "App frontend custom domain."
  default     = "app.example.com"
}

variable "admin_domain_name" {
  type        = string
  description = "Admin frontend custom domain."
  default     = "admin.example.com"
}

variable "route53_zone_name" {
  type        = string
  description = "Existing public Route 53 hosted zone name used for DNS validation records."
  default     = "example.com"
}

variable "initial_admin_username" {
  type        = string
  description = "Initial Cognito admin username."
}

variable "initial_admin_email" {
  type        = string
  description = "Initial Cognito admin email."
}

variable "initial_admin_temp_password" {
  type        = string
  description = "Temporary password for the initial admin. Must satisfy Cognito policy."
  sensitive   = true
}

variable "second_admin_username" {
  type        = string
  description = "Optional second Cognito admin username. Leave blank to skip creating it."
  default     = ""
}

variable "second_admin_email" {
  type        = string
  description = "Optional second Cognito admin email. Required when second_admin_username is set."
  default     = ""
}

variable "second_admin_temp_password" {
  type        = string
  description = "Optional temporary password for the second admin. Must satisfy Cognito policy when set."
  default     = ""
  sensitive   = true
}

variable "protect_identity_data" {
  type        = bool
  description = "When true, enable production-lite critical identity/data service deletion protection."
  default     = true
}

variable "monthly_budget_limit_usd" {
  type        = string
  description = "Monthly AWS Budget limit in USD for the seasonal teaching deployment."
  default     = "50"
}
