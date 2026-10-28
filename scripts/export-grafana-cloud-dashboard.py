"""Create a Grafana Cloud import file from the provisioned VedaOps dashboard."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "monitoring" / "grafana" / "dashboards" / "vedaops-overview.json"
OUTPUT = ROOT / "monitoring" / "grafana" / "dashboards" / "vedaops-overview-cloud.json"


def main() -> int:
    dashboard = json.loads(SOURCE.read_text(encoding="utf-8"))
    dashboard["__inputs"] = [
        {
            "name": "DS_PROMETHEUS",
            "label": "Prometheus",
            "description": "Grafana Cloud Prometheus data source",
            "type": "datasource",
            "pluginId": "prometheus",
            "pluginName": "Prometheus",
        }
    ]

    for panel in dashboard.get("panels", []):
        datasource = panel.get("datasource")
        if isinstance(datasource, dict) and datasource.get("uid") == "prometheus":
            datasource["uid"] = "${DS_PROMETHEUS}"
        for target in panel.get("targets", []):
            expression = target.get("expr")
            if not isinstance(expression, str):
                continue
            expression = expression.replace(
                'container_label_com_docker_compose_project="vedaops"',
                'container_label_com_docker_compose_project=~"vedaops(-staging|-production)?"',
            )
            expression = expression.replace(
                'name=~".*vedaops-app.*"', 'name=~".*vedaops.*app.*"'
            )
            target["expr"] = expression

    OUTPUT.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    print(f"Created {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
