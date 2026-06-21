# Production-lite release checklist

Use this checklist for the 50-user, low-traffic July/August teaching deployment. It keeps the release path repeatable without adding a full CI/CD service.

## Pre-release checks

- [ ] Confirm `infra/terraform.tfvars` uses real admin values and keeps `protect_identity_data = true`.
- [ ] Confirm the alert email in `initial_admin_email` can receive AWS SNS and Budget notifications.
- [ ] Confirm the Terraform plan includes DynamoDB Point-in-Time Recovery, S3 versioning, error-only Lambda application logs, AWS Budget notifications, and the `magic=true` Budget tag filter.
- [ ] Confirm `magic` is active as an AWS cost allocation tag before relying on tag-scoped Budget totals. AWS cost allocation tag reporting can lag after first activation.

## Local validation

Run these commands from the repository root:

```bash
backend/.venv/bin/pytest -q
backend/.venv/bin/ruff check backend

cd frontend
npm run build

cd ../infra
terraform fmt -recursive -check
terraform validate
terraform plan
```

## Release

Run these commands from the repository root after reviewing the plan:

```bash
cd infra
terraform apply

cd ..
./scripts/fetch-magic-pages.sh
./scripts/deploy-static.sh
./scripts/smoke-test.sh
```

## Post-release checks

- [ ] Open the app and admin CloudFront URLs from `terraform output`.
- [ ] Log in as admin and verify user, teacher, and week access screens load.
- [ ] Verify students only see opened weeks and private content is loaded through signed URLs.
- [ ] Confirm CloudWatch alarms and AWS Budget notifications target the expected email.
- [ ] Confirm successful 200 API requests do not create API access log entries; only Lambda-handled API errors write structured `api_error` / `unexpected_error` log lines.
- [ ] Confirm the Budget cost filter is `TagKeyValue = user:magic$true`, so other services in the same AWS account are excluded.
- [ ] Keep DynamoDB Point-in-Time Recovery and S3 versioning enabled until the August class data-retention window ends.
