resource "aws_ce_cost_allocation_tag" "magic" {
  tag_key = "magic"
  status  = "Active"
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name_prefix}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:magic$true"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 10
    threshold_type             = "ABSOLUTE_VALUE"
    subscriber_email_addresses = [var.initial_admin_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 20
    threshold_type             = "ABSOLUTE_VALUE"
    subscriber_email_addresses = [var.initial_admin_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 50
    threshold_type             = "ABSOLUTE_VALUE"
    subscriber_email_addresses = [var.initial_admin_email]
  }
}
