# VedaOps operations runbook

## Service map

| Component | Local address / port | Purpose |
|---|---|---|
| Nginx and app | `http://127.0.0.1:8080` | Demo application and health route |
| Prometheus | `http://127.0.0.1:9090` | Metrics, alert rules, and target status |
| Grafana | `http://127.0.0.1:3000` | Provisioned VedaOps dashboard |
| Alertmanager | Compose network only, `alertmanager:9093` | Groups and forwards firing alerts |
| Healer | Compose network only, `healer:8000` | Alert webhook and in-memory incident summaries |
| cAdvisor | Compose network only, `cadvisor:8080` | Container metrics |
| Node Exporter | Compose network only, `node-exporter:9100` | Linux host metrics |

The published web and monitoring ports bind to loopback by default. Staging uses 8081/9091/3001 and production uses 8080/9090/3000 on a shared host. The healer acknowledges each firing webhook before processing it in the background. Do not expose Prometheus, Grafana, Alertmanager, or the healer directly to the public internet.

## Health and monitoring checks

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8080/health
```

Open Prometheus `/targets`; the `app`, `cadvisor`, and `node` jobs should report `UP`. Grafana's provisioned dashboard is in the VedaOps folder. Allow about one minute for initial metrics and alert evaluation.

View service logs:

```powershell
docker compose logs --tail=100 app healer alertmanager prometheus
```

## When an incident arrives

1. Read the Telegram message or healer log entry. The message includes the alert, diagnosis, chosen action, and action result.
2. Check the health endpoint and `docker compose ps`.
3. If the healer says `notify_human`, inspect app logs and Prometheus targets before taking action. The healer deliberately does not retry a restart loop after three restart requests in one hour.
4. If an automatic restart fails, run `docker compose up -d app`, then `scripts/smoke-test.ps1`.
5. If failures continue, preserve logs, stop repeated chaos tests, and investigate the app or host before changing the allowlist or restart limit.

## Chaos demo

Run `scripts/chaos-kill.ps1` from PowerShell or `bash scripts/chaos-kill.sh` from Bash. They permit only `vedaops-app` (local) or `vedaops-staging-app` (staging), select the matching health port, and refuse production or other containers. Do this only in the local demo or a staging environment. To exercise staging, use `./scripts/chaos-kill.ps1 -Container vedaops-staging-app` or `bash scripts/chaos-kill.sh vedaops-staging-app`.

## Rollback

Deployments use a commit SHA image tag and separate Compose projects. Find the last healthy tag in the GitHub Actions run history, then on the server run the commands in the matching staging or production project directory. For example, production:

```bash
APP_IMAGE=ghcr.io/OWNER/vedaops-app:PREVIOUS_SHA COMPOSE_PROJECT_NAME=vedaops-production APP_PORT=8080 APP_CONTAINER_NAME=vedaops-production-app HEALER_ALLOWED_CONTAINERS=vedaops-production-app docker compose pull app
APP_IMAGE=ghcr.io/OWNER/vedaops-app:PREVIOUS_SHA COMPOSE_PROJECT_NAME=vedaops-production APP_PORT=8080 APP_CONTAINER_NAME=vedaops-production-app HEALER_ALLOWED_CONTAINERS=vedaops-production-app docker compose up -d --no-build app
curl --fail http://127.0.0.1:8080/health
```

Replace `OWNER` and `PREVIOUS_SHA` with the actual GHCR owner and commit SHA. Keep the previous image in GHCR until the new deployment has passed its smoke check.

## Rotate credentials

1. Create a replacement Anthropic key or Telegram bot token in its provider's official account interface.
2. Update the value in the server's ignored `.env` file. GitHub Environment secrets configure SSH deployment access; the workflow does not copy Anthropic or Telegram credentials to the server. Never paste a credential into a command, issue, screenshot, or repository file.
3. Restart the affected service with `docker compose up -d --force-recreate healer`.
4. Verify a test notification or incident. Revoke the old credential at the provider.
5. If a credential was committed, revoke it immediately; deleting the file in a later commit does not remove it from Git history.

## Known limits

- Docker Desktop's Linux VM can report container and host metrics differently from a native Linux server. Confirm Prometheus targets and the cAdvisor container labels before relying on an alert.
- Anthropic and Telegram integrations need their own accounts and credentials. AI requests can incur usage charges.
- `docker compose down --volumes` removes local monitoring history and dashboard state. Use it only when that data can be discarded.
