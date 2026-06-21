resource "aws_cognito_user_pool" "main" {
  name                = "${local.name_prefix}-users"
  deletion_protection = var.protect_identity_data ? "ACTIVE" : "INACTIVE"

  username_attributes      = []
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 10
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "${local.name_prefix}-pwa-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret               = false
  explicit_auth_flows           = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors = "ENABLED"
  access_token_validity         = 3
  id_token_validity             = 3
  refresh_token_validity        = 7
  supported_identity_providers  = ["COGNITO"]

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_group" "groups" {
  for_each     = toset(["admin", "teacher", "student"])
  name         = each.key
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user" "initial_admin" {
  user_pool_id       = aws_cognito_user_pool.main.id
  username           = var.initial_admin_username
  temporary_password = var.initial_admin_temp_password
  message_action     = "SUPPRESS"

  attributes = {
    email          = var.initial_admin_email
    email_verified = "true"
  }
}

resource "aws_cognito_user_in_group" "initial_admin" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = aws_cognito_user.initial_admin.username
  group_name   = aws_cognito_user_group.groups["admin"].name
}

resource "aws_cognito_user" "second_admin" {
  count = local.second_admin_requested ? 1 : 0

  user_pool_id       = aws_cognito_user_pool.main.id
  username           = var.second_admin_username
  temporary_password = var.second_admin_temp_password
  message_action     = "SUPPRESS"

  attributes = {
    email          = var.second_admin_email
    email_verified = "true"
  }

  lifecycle {
    precondition {
      condition     = var.second_admin_username != "" && var.second_admin_email != "" && var.second_admin_temp_password != ""
      error_message = "second_admin_username, second_admin_email, and second_admin_temp_password must all be set together."
    }
  }
}

resource "aws_cognito_user_in_group" "second_admin" {
  count = length(aws_cognito_user.second_admin)

  user_pool_id = aws_cognito_user_pool.main.id
  username     = aws_cognito_user.second_admin[0].username
  group_name   = aws_cognito_user_group.groups["admin"].name
}
