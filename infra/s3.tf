resource "aws_s3_bucket" "app_frontend" {
  bucket        = "${local.name_prefix}-app-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = !var.protect_identity_data

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket" "admin_frontend" {
  bucket        = "${local.name_prefix}-admin-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = !var.protect_identity_data

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket" "content" {
  bucket        = "${local.name_prefix}-content-${data.aws_caller_identity.current.account_id}"
  force_destroy = !var.protect_identity_data

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "app_frontend" {
  bucket = aws_s3_bucket.app_frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "admin_frontend" {
  bucket = aws_s3_bucket.admin_frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "content" {
  bucket = aws_s3_bucket.content.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = {
    app     = aws_s3_bucket.app_frontend.id
    admin   = aws_s3_bucket.admin_frontend.id
    content = aws_s3_bucket.content.id
  }

  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


resource "aws_s3_bucket_cors_configuration" "content" {
  bucket = aws_s3_bucket.content.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT"]
    allowed_origins = ["https://${var.app_domain_name}"]
    max_age_seconds = 3000
  }
}
