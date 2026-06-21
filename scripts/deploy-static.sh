#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_OUTPUT() {
  if ! command -v terraform >/dev/null 2>&1; then
    printf 'ERROR: terraform is not installed and %s was not provided by environment.\n' "$1" >&2
    exit 127
  fi
  (cd "$ROOT_DIR/infra" && terraform output -raw "$1")
}
CHECK_REQUIRED_CI_ENV() {
  [[ "${CI:-}" == "true" ]] || return 0
  local missing=()
  local name
  for name in "$@"; do
    [[ -n "${!name:-}" ]] || missing+=("$name")
  done
  if (( ${#missing[@]} > 0 )); then
    printf 'ERROR: Missing required environment variables: %s\n' "${missing[*]}" >&2
    printf 'Provide them in the environment before running this script.\n' >&2
    exit 1
  fi
}
CHECK_REQUIRED_CI_ENV \
  VITE_API_BASE_URL \
  VITE_COGNITO_USER_POOL_ID \
  VITE_COGNITO_CLIENT_ID \
  APP_FRONTEND_BUCKET \
  ADMIN_FRONTEND_BUCKET \
  CONTENT_BUCKET \
  APP_CLOUDFRONT_DOMAIN_NAME \
  ADMIN_CLOUDFRONT_DOMAIN_NAME \
  APP_CLOUDFRONT_DISTRIBUTION_ID \
  ADMIN_CLOUDFRONT_DISTRIBUTION_ID
INVALIDATE_DISTRIBUTION() {
  local label="$1"
  local distribution_id="$2"
  local invalidation_id
  printf 'Invalidating %s CloudFront distribution: %s
' "$label" "$distribution_id"
  invalidation_id="$(aws cloudfront create-invalidation --distribution-id "$distribution_id" --paths "/*" --query 'Invalidation.Id' --output text)"
  aws cloudfront wait invalidation-completed --distribution-id "$distribution_id" --id "$invalidation_id"
}

export VITE_API_BASE_URL="${VITE_API_BASE_URL:-$(TF_OUTPUT api_gateway_url)}"
export VITE_COGNITO_USER_POOL_ID="${VITE_COGNITO_USER_POOL_ID:-$(TF_OUTPUT cognito_user_pool_id)}"
export VITE_COGNITO_CLIENT_ID="${VITE_COGNITO_CLIENT_ID:-$(TF_OUTPUT cognito_user_pool_client_id)}"
APP_BUCKET="${APP_FRONTEND_BUCKET:-$(TF_OUTPUT app_frontend_bucket)}"
ADMIN_BUCKET="${ADMIN_FRONTEND_BUCKET:-$(TF_OUTPUT admin_frontend_bucket)}"
CONTENT_BUCKET="${CONTENT_BUCKET:-$(TF_OUTPUT content_bucket)}"
APP_DIST="${APP_CLOUDFRONT_DOMAIN_NAME:-$(TF_OUTPUT app_cloudfront_domain_name)}"
ADMIN_DIST="${ADMIN_CLOUDFRONT_DOMAIN_NAME:-$(TF_OUTPUT admin_cloudfront_domain_name)}"
APP_DISTRIBUTION_ID="${APP_CLOUDFRONT_DISTRIBUTION_ID:-$(TF_OUTPUT app_cloudfront_distribution_id)}"
ADMIN_DISTRIBUTION_ID="${ADMIN_CLOUDFRONT_DISTRIBUTION_ID:-$(TF_OUTPUT admin_cloudfront_distribution_id)}"

cd "$ROOT_DIR/frontend"
npm install
npm run build

aws s3 rm "s3://$APP_BUCKET/magic-pages/" --recursive
aws s3 rm "s3://$ADMIN_BUCKET/magic-pages/" --recursive
aws s3 sync dist/ "s3://$APP_BUCKET/" --delete --exclude "magic-pages/*"
aws s3 sync dist/ "s3://$ADMIN_BUCKET/" --delete --exclude "magic-pages/*"
aws s3 sync dist/magic-pages/ "s3://$CONTENT_BUCKET/magic-pages/" --delete
INVALIDATE_DISTRIBUTION "app" "$APP_DISTRIBUTION_ID"
INVALIDATE_DISTRIBUTION "admin" "$ADMIN_DISTRIBUTION_ID"
printf 'Synced app/admin assets and private magic pages. CloudFront domains: %s %s\n' "$APP_DIST" "$ADMIN_DIST"
