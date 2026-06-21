# AWS Well-Architected IaC Review

Generated: 2026-06-07T05:47:49+00:00

## Scope

- Terraform files scanned: 14
- Findings: 28
- Mode: static Terraform text analysis only; no AWS credentials, provider downloads, or Terraform apply.

## Summary

Scanned files:
- `infra/acm.tf`
- `infra/alarms.tf`
- `infra/api_gateway.tf`
- `infra/budgets.tf`
- `infra/cloudfront.tf`
- `infra/cognito.tf`
- `infra/dynamodb.tf`
- `infra/lambda.tf`
- `infra/locals.tf`
- `infra/outputs.tf`
- `infra/providers.tf`
- `infra/s3.tf`
- `infra/variables.tf`
- `infra/versions.tf`

| Severity | Count |
| --- | ---: |
| High | 0 |
| Medium | 0 |
| Low | 28 |

## Checks Without Findings

- `SEC-S3-PUBLIC`
- `SEC-SG-PUBLIC-INGRESS`
- `REL-RDS-BACKUP`
- `REL-RDS-MULTIAZ`
- `OPS-CW-LOGS`
- `OPS-CW-ALARMS`
- `COST-EC2-OVERSIZED`
- `COST-BUDGET`
- `PERF-SCALING`
- `PERF-CACHE`

## Findings

### Operational Excellence

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/acm.tf` resource `aws_acm_certificate_validation.frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/acm.tf` resource `aws_route53_record.frontend_certificate_validation`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/alarms.tf` resource `aws_sns_topic_subscription.alerts_email`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_authorizer.jwt`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_integration.lambda`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_route.options_proxy`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_route.options_root`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_route.proxy`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_apigatewayv2_route.root`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/api_gateway.tf` resource `aws_lambda_permission.api_gateway`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/budgets.tf` resource `aws_budgets_budget.monthly`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/budgets.tf` resource `aws_ce_cost_allocation_tag.magic`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cloudfront.tf` resource `aws_cloudfront_origin_access_control.frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cloudfront.tf` resource `aws_s3_bucket_policy.admin_frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cloudfront.tf` resource `aws_s3_bucket_policy.app_frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user.initial_admin`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user.second_admin`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user_group.groups`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user_in_group.initial_admin`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user_in_group.second_admin`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/cognito.tf` resource `aws_cognito_user_pool_client.app`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/dynamodb.tf` resource `aws_dynamodb_table_item.initial_admin_profile`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/dynamodb.tf` resource `aws_dynamodb_table_item.second_admin_profile`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/lambda.tf` resource `aws_iam_role_policy.lambda`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/s3.tf` resource `aws_s3_bucket_cors_configuration.content`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/s3.tf` resource `aws_s3_bucket_versioning.admin_frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/s3.tf` resource `aws_s3_bucket_versioning.app_frontend`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

#### AWS resource missing tags (`OPS-TAGS`)

- Severity: **LOW**
- Location: `infra/s3.tf` resource `aws_s3_bucket_versioning.content`
- Evidence: AWS resource has no tags block for ownership, environment, or cost allocation.
- Recommendation: Add common tags such as Project, Environment, Owner, and ManagedBy.

## Next Steps

- Review high-severity findings before merging infrastructure changes.
- Keep exceptions documented with workload context, owner, and expiry date.
- Run this reviewer in pull requests alongside `terraform fmt` and unit tests.
