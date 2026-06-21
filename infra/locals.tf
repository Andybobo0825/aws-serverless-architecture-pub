locals {
  name_prefix            = "${var.project_name}-${var.environment}"
  second_admin_requested = var.second_admin_username != "" || var.second_admin_email != ""

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Name        = "${var.project_name}-${var.environment}"
    magic       = "true"
  }
}
