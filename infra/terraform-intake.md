# Terraform Intake — Magic Serverless MVP

## Detected app stack

- Repository is a greenfield workspace for this project.
- Existing files before implementation planning: `plan.md`, approved design spec, architecture diagrams.
- No existing application framework, package manager, Terraform, Docker, or CI files were detected.

## Selected cloud/provider/region

- Cloud provider: AWS.
- Primary region: `ap-northeast-1`.
- ACM certificate region for CloudFront: `us-east-1`.
- Domain: `example.com` already exists in Route 53.
- Terraform will not create Route 53 hosted zones; it manages the ACM DNS validation CNAME records in the existing public hosted zone.

## Environment purpose

- Production-lite seasonal teaching deployment after MVP.
- Approximately 50 users.
- Lowest practical serverless cost.
- Required service window is July/August, with data retained through the seasonal teaching period.
- `terraform destroy` remains available after end-of-season review, but identity/data protection is enabled during the service window.

## Runtime model

- Frontend: static PWA served from S3 through CloudFront.
- API: API Gateway HTTP API + Lambda Python 3.12.
- Auth: Cognito User Pool + groups.
- Data: DynamoDB on-demand tables.
- Content: private S3 content bucket for PDFs and controlled magic HTML assets.

## Services

- Cognito User Pool, User Pool Client, groups, initial admin user.
- API Gateway HTTP API with JWT authorizer.
- Lambda Python 3.12.
- DynamoDB tables: `magic-users`, `magic-weeks`, `magic-class-access`.
- S3 buckets: app frontend, admin frontend, content/PDF.
- CloudFront distributions for `app.example.com` and `admin.example.com`.
- ACM DNS-validated certificate in `us-east-1`.
- CloudWatch Lambda logs with short MVP retention.
- API Gateway all-request access logs are intentionally disabled because HTTP API access logs do not natively filter out 200 responses.
- Lambda writes structured `api_error` / `unexpected_error` entries only when the API returns an error, keeping normal 200 traffic out of CloudWatch Logs.
- SNS email alerts for Lambda/API failures.
- AWS Budget monthly cost notifications scoped to AWS costs tagged `magic=true`.

## Security/networking

- No VPC/NAT for Lambda in MVP.
- Frontend buckets private through CloudFront OAC.
- Content/PDF bucket private.
- API validates Cognito JWT and Lambda enforces role, active status, device binding, and Week access.
- Admin cannot view existing passwords; admin can reset passwords.
- Initial and optional second admin credentials are supplied from local `infra/terraform.tfvars`, which is ignored by git; `infra/terraform.tfvars.example` documents required keys without secrets.
- Cognito deletion protection is enabled by default for production-lite identity data.
- DynamoDB Point-in-Time Recovery is enabled for users, weeks, and class access tables.
- S3 versioning is enabled for app, admin, and content buckets.

## Cost and cleanup

- DynamoDB on-demand.
- CloudWatch retention 7–14 days.
- AWS Budget is enabled with 10/20/50 USD absolute-value email notifications.
- The Budget uses a `TagKeyValue` cost filter for `user:magic$true`, and Terraform activates the `magic` cost allocation tag.
- No WAF, NAT Gateway, RDS, VPC endpoints, CI/CD, or production backup resources in MVP.
- S3 buckets still use Terraform settings/scripts that allow destroy after end-of-season content cleanup.

## Release process

- Full CI/CD is intentionally omitted for this short-lived, low-traffic deployment.
- `docs/release-checklist.md` is the production-lite release runbook.
- Release sequence: backend tests and lint, frontend build, Terraform fmt/validate/plan/apply, static asset deploy, smoke test.

## Naming/tagging

- Resource names use `magic-*`.
- Common Terraform tags include `Project=magic`, `Environment=mvp`, `Name=magic-mvp`, and `magic=true` to satisfy the deployment IAM user's tag-gated permissions.

## Open questions

- None for MVP implementation planning.
