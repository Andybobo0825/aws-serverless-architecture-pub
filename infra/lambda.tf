data "archive_file" "api" {
  type        = "zip"
  source_dir  = "${path.module}/../backend"
  output_path = "${path.module}/build/magic-api.zip"
  excludes    = [".venv", ".pytest_cache", ".ruff_cache", "tests", "__pycache__", "magic_api/__pycache__"]
}

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Scan"]
        Resource = [aws_dynamodb_table.users.arn, aws_dynamodb_table.weeks.arn, aws_dynamodb_table.class_access.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.content.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.content.arn
      },
      {
        Effect   = "Allow"
        Action   = ["cognito-idp:AdminGetUser", "cognito-idp:AdminCreateUser", "cognito-idp:AdminSetUserPassword", "cognito-idp:AdminListGroupsForUser", "cognito-idp:AdminAddUserToGroup", "cognito-idp:AdminRemoveUserFromGroup", "cognito-idp:AdminDisableUser", "cognito-idp:AdminEnableUser", "cognito-idp:AdminDeleteUser"]
        Resource = aws_cognito_user_pool.main.arn
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name_prefix}-api"
  retention_in_days = 14

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name_prefix}-api"
  role             = aws_iam_role.lambda.arn
  handler          = "magic_api.app.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256
  timeout          = 15
  memory_size      = 256

  environment {
    variables = {
      USERS_TABLE_NAME        = aws_dynamodb_table.users.name
      WEEKS_TABLE_NAME        = aws_dynamodb_table.weeks.name
      CLASS_ACCESS_TABLE_NAME = aws_dynamodb_table.class_access.name
      CONTENT_BUCKET_NAME     = aws_s3_bucket.content.bucket
      COGNITO_USER_POOL_ID    = aws_cognito_user_pool.main.id
      PDF_URL_TTL_SECONDS     = "300"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api]

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}
