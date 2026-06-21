#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT_DIR/infra/build"
(cd "$ROOT_DIR/infra" && terraform fmt -recursive && terraform validate)
echo "Terraform archive_file will package backend/magic_api during plan/apply."