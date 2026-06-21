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
  APP_CLOUDFRONT_DOMAIN_NAME \
  ADMIN_CLOUDFRONT_DOMAIN_NAME

API_URL="${VITE_API_BASE_URL:-$(TF_OUTPUT api_gateway_url)}"
APP_DOMAIN="${APP_CLOUDFRONT_DOMAIN_NAME:-$(TF_OUTPUT app_cloudfront_domain_name)}"
ADMIN_DOMAIN="${ADMIN_CLOUDFRONT_DOMAIN_NAME:-$(TF_OUTPUT admin_cloudfront_domain_name)}"
printf 'API URL: %s\n' "$API_URL"
printf 'App CloudFront: https://%s\n' "$APP_DOMAIN"
printf 'Admin CloudFront: https://%s\n' "$ADMIN_DOMAIN"
curl -fsSI "https://$APP_DOMAIN" >/dev/null
curl -fsSI "https://$ADMIN_DOMAIN" >/dev/null
for DOMAIN in "$APP_DOMAIN" "$ADMIN_DOMAIN"; do
  if curl -fsSL "https://$DOMAIN/magic-pages/mindreading.html" | grep -q "心靈感應"; then
    printf 'ERROR: https://%s/magic-pages/mindreading.html still serves public magic page content.\n' "$DOMAIN" >&2
    exit 1
  fi
done
printf 'Static smoke checks passed. Protected API requires Cognito token and is not called here.\n'
