#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:?Usage: render-runtime-monitoring.sh <compose-project-name>}"
if [[ ! "$PROJECT_NAME" =~ ^vedaops(-[a-z0-9]+)?$ ]]; then
  printf 'Unsupported VedaOps Compose project name: %s\n' "$PROJECT_NAME" >&2
  exit 2
fi

RUNTIME_DIR="${2:-.runtime}"
mkdir -p "$RUNTIME_DIR/dashboards"

sed 's|container_label_com_docker_compose_project="vedaops"|container_label_com_docker_compose_project="'"$PROJECT_NAME"'"|g' \
  monitoring/alert.rules.yml > "$RUNTIME_DIR/alert.rules.yml"
sed 's|container_label_com_docker_compose_project=\\"vedaops\\"|container_label_com_docker_compose_project=\\"'"$PROJECT_NAME"'\\"|g' \
  monitoring/grafana/dashboards/vedaops-overview.json \
  > "$RUNTIME_DIR/dashboards/vedaops-overview.json"

printf 'Rendered alert and dashboard filters for Compose project %s in %s\n' \
  "$PROJECT_NAME" "$RUNTIME_DIR"
