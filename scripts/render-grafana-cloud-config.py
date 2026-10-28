"""Render an ignored Prometheus config for optional Grafana Cloud forwarding."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TOKEN_FILE = ROOT / ".secrets" / "grafana_cloud_token"
SOURCE_CONFIG = ROOT / "monitoring" / "prometheus.yml"
OUTPUT_CONFIG = ROOT / ".runtime" / "prometheus-cloud.yml"


def read_project_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    values.update(os.environ)
    return values


def main() -> int:
    values = read_project_env()
    endpoint = values.get("GRAFANA_CLOUD_PROMETHEUS_URL", "").strip()
    username = values.get("GRAFANA_CLOUD_PROMETHEUS_USERNAME", "").strip()

    parsed_endpoint = urlsplit(endpoint)
    if (
        parsed_endpoint.scheme != "https"
        or not parsed_endpoint.hostname
        or not parsed_endpoint.path.endswith("/api/prom/push")
        or parsed_endpoint.query
        or parsed_endpoint.fragment
    ):
        raise SystemExit(
            "Set GRAFANA_CLOUD_PROMETHEUS_URL in .env to the HTTPS remote-write "
            "endpoint ending in /api/prom/push."
        )
    if not username:
        raise SystemExit("Set GRAFANA_CLOUD_PROMETHEUS_USERNAME in .env.")
    if not TOKEN_FILE.is_file() or not TOKEN_FILE.read_text(encoding="utf-8").strip():
        raise SystemExit(
            "Create .secrets/grafana_cloud_token and save the metrics:write token there."
        )

    config = SOURCE_CONFIG.read_text(encoding="utf-8")
    local_alerting = (
        "rule_files:\n"
        "  - /etc/prometheus/alert.rules.yml\n\n"
        "alerting:\n"
        "  alertmanagers:\n"
        "    - static_configs:\n"
        '        - targets: ["alertmanager:9093"]\n\n'
    )
    if config.count(local_alerting) != 1:
        raise SystemExit("Unexpected alerting config; refusing to render.")
    config = config.replace(local_alerting, "", 1)
    marker = "  evaluation_interval: 10s\n"
    if config.count(marker) != 1:
        raise SystemExit("Unexpected Prometheus config layout; refusing to render.")
    config = config.replace(
        marker,
        marker + "  external_labels:\n    origin_prometheus: vedaops\n",
        1,
    )
    config += (
        "\nremote_write:\n"
        "  - url: "
        + json.dumps(endpoint)
        + "\n"
        "    basic_auth:\n"
        "      username: "
        + json.dumps(username)
        + "\n"
        "      password_file: /run/secrets/grafana_cloud_token\n"
    )
    OUTPUT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CONFIG.write_text(config, encoding="utf-8", newline="\n")
    print(f"Rendered optional Grafana Cloud config to {OUTPUT_CONFIG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
