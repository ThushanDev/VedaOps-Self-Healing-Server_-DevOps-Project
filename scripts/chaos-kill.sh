#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${1:-vedaops-app}"
case "$CONTAINER" in
  vedaops-app) DEFAULT_BASE_URL="http://127.0.0.1:8080" ;;
  vedaops-staging-app) DEFAULT_BASE_URL="http://127.0.0.1:8081" ;;
  *)
    printf 'Refusing to kill non-demo/non-staging container: %s\n' "$CONTAINER" >&2
    exit 2
    ;;
esac

echo "Stopping allowlisted demo/staging container $CONTAINER. Watch Grafana and the healer logs."
docker kill "$CONTAINER"
"$(dirname "$0")/smoke-test.sh" "${BASE_URL:-$DEFAULT_BASE_URL}" 30
