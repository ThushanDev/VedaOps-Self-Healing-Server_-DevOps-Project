#!/usr/bin/env bash
set -euo pipefail

python3.12 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --requirement app/requirements.txt --requirement healer/requirements.txt --requirement requirements-dev.txt
ruff check app healer
pytest
docker compose config --quiet
docker run --rm --volume "$PWD/monitoring:/etc/prometheus:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check config /etc/prometheus/prometheus.yml
docker run --rm --volume "$PWD/monitoring:/etc/prometheus:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check rules /etc/prometheus/alert.rules.yml
docker run --rm --volume "$PWD/monitoring:/etc/alertmanager:ro" --entrypoint=/bin/amtool prom/alertmanager:v0.34.1 check-config /etc/alertmanager/alertmanager.yml
for project in vedaops vedaops-staging vedaops-production; do
  bash scripts/render-runtime-monitoring.sh "$project"
  docker run --rm --volume "$PWD/.runtime:/etc/runtime:ro" --entrypoint=/bin/promtool prom/prometheus:v3.15.0 check rules /etc/runtime/alert.rules.yml
  jq -e --arg project "$project" '.panels[1].targets[0].expr | contains("container_label_com_docker_compose_project=\"" + $project + "\"")' .runtime/dashboards/vedaops-overview.json > /dev/null
done
docker compose build
echo "Python, shell, Compose, monitoring, and container build checks passed."
