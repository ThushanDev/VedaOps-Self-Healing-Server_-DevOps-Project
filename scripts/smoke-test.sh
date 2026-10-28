#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"
ATTEMPTS="${2:-10}"

for ((attempt = 1; attempt <= ATTEMPTS; attempt++)); do
  if curl --fail --silent --show-error --max-time 3 "${BASE_URL%/}/health"; then
    printf '\nSmoke test passed: %s/health\n' "${BASE_URL%/}"
    exit 0
  fi
  sleep 3
done

printf 'Smoke test failed after %s attempts: %s/health\n' "$ATTEMPTS" "${BASE_URL%/}" >&2
exit 1
