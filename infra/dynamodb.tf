resource "aws_dynamodb_table" "users" {
  name                        = "${local.name_prefix}-users"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "username"
  deletion_protection_enabled = var.protect_identity_data

  attribute {
    name = "username"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_dynamodb_table" "weeks" {
  name                        = "${local.name_prefix}-weeks"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "week_id"
  deletion_protection_enabled = var.protect_identity_data

  attribute {
    name = "week_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_dynamodb_table" "class_access" {
  name                        = "${local.name_prefix}-class-access"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "class_id"
  deletion_protection_enabled = var.protect_identity_data

  attribute {
    name = "class_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}


resource "aws_dynamodb_table_item" "initial_admin_profile" {
  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    username             = { S = var.initial_admin_username }
    role                 = { S = "admin" }
    status               = { S = "active" }
    identity_sync_status = { S = "synced" }
    classes              = { L = [] }
  })
}


resource "aws_dynamodb_table_item" "second_admin_profile" {
  count = local.second_admin_requested ? 1 : 0

  table_name = aws_dynamodb_table.users.name
  hash_key   = aws_dynamodb_table.users.hash_key

  item = jsonencode({
    username             = { S = var.second_admin_username }
    role                 = { S = "admin" }
    status               = { S = "active" }
    identity_sync_status = { S = "synced" }
    classes              = { L = [] }
  })
}
