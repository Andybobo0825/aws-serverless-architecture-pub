# Magic MVP Deployment

## Prerequisites

- AWS CLI authenticated to the target account.
- Terraform >= 1.6.
- Node.js >= 20.
- Python 3.12.
- Route 53 hosted zone for `example.com` already exists.
- AWS Budget notification email access for the initial admin email.
- AWS Cost Explorer/Billing permission to activate the `magic` cost allocation tag used by the tag-scoped Budget.
- The deployment IAM policy must allow create actions that use `aws:RequestTag/magic=true` and must not explicitly deny `acm:RequestCertificate`.

## Deploy

Create a local `infra/terraform.tfvars` from the example and fill in real values.
Terraform auto-loads this file during `plan`, `apply`, and `destroy`; do not commit it.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars
terraform init
terraform plan
terraform apply
terraform output acm_dns_validation_records
```

Add the ACM DNS validation records in Route 53 Console. After validation, run `terraform apply` again if CloudFront needs to finish certificate attachment.

Then deploy static assets:

```bash
./scripts/fetch-magic-pages.sh
./scripts/deploy-static.sh
./scripts/smoke-test.sh
```

## Public portfolio snapshot

This public snapshot intentionally omits GitHub Actions workflows. Use the local deploy scripts only after supplying your own AWS configuration.

For the repeatable production-lite sequence, use `docs/release-checklist.md`.

## Manual DNS

Create Route 53 records manually:

- `app.example.com` -> app CloudFront distribution domain.
- `admin.example.com` -> admin CloudFront distribution domain.

Terraform intentionally does not manage Route 53 records.

## Destroy MVP

```bash
cd infra
terraform destroy
```

Production-lite defaults enable Cognito deletion protection, DynamoDB Point-in-Time Recovery, S3 versioning, error-only Lambda application logs, and AWS Budget notifications scoped to resources tagged `magic=true`. S3 buckets still use `force_destroy` for end-of-season cleanup, so review `terraform plan` carefully before destroy.
