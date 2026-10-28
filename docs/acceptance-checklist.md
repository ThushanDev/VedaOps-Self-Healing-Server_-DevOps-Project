# Release acceptance checklist

Use this checklist to distinguish files prepared in the repository from results that need a real local run or GitHub/server access. Do not mark a runtime or cloud item complete from configuration alone.

## Repository checks

- [ ] Clone or copy the project into the target repository and review `git status`; confirm `.env`, API keys, bot tokens, and private keys are absent.
- [ ] Run `scripts/verify.sh` on Linux/macOS, or the equivalent commands in the README on Windows. Record Ruff, pytest, Compose, Prometheus, Alertmanager, runtime rendering, and image build results.
- [ ] Push a feature branch and confirm the `checks` and `secrets` GitHub Actions jobs pass. Fix any Trivy or Gitleaks findings before merging.
- [ ] Protect `main` and require both CI checks before merge.

## Local stack and incident demo

- [ ] Run `docker compose up --build -d`, confirm all expected containers are running with `docker compose ps`, and verify the app and healer health checks plus `/health` (`{"status":"ok"}`).
- [ ] Open Prometheus `/targets`; confirm the `app`, `cadvisor`, and `node` targets are up. Confirm the VedaOps dashboard loads in Grafana.
- [ ] Run the guarded chaos script in a local or staging environment. Verify the app recovers or requests human review according to the configured credentials and limits.
- [ ] If Anthropic is enabled, verify the AI response, secret redaction, one-call-per-minute limit, and fallback behavior with an invalid key or malformed response. Check the provider spending limit first.
- [ ] If Telegram is enabled, verify the incident message includes alert, cause, action, and result.
- [ ] Capture real screenshots of the passing CI run, Grafana dashboard, and Telegram incident. Record a short crash-to-recovery demo only after observing a real run. Do not use mock results as evidence.

## GitHub and remote deployment

- [ ] Create the `staging` and `production` GitHub Environments. Add the SSH secrets documented in the README and set the deployment enable variables only after both hosts/paths are ready.
- [ ] Configure staging first and confirm the workflow deploys the exact CI commit and passes its host-local smoke check.
- [ ] On a shared host, stop only the staging app and confirm staging alerts for it while production monitoring stays clear; repeat against production.
- [ ] Add required reviewers to `production`; verify production waits for approval and deploys only after staging succeeds.
- [ ] Keep the app's Anthropic and Telegram credentials in the server's ignored `.env`. Keep GitHub deploy credentials in GitHub Environment secrets.
- [ ] Confirm server firewall/TLS setup, GHCR access, monitoring access restrictions, and rollback to a prior image tag.
- [ ] Export `docs/assets/vedaops-social-preview.svg` to a raster image, set it in the target GitHub repository's social preview, and pin the repository if desired.

## Current evidence

The source includes unit tests, CI/deploy workflows, Compose and monitoring configuration, Grafana dashboard provisioning, brand assets, and operational docs. On 2026-10-29, Python 3.12.10 passed Ruff and all 15 pytest tests in the target repository clone. Standalone Uvicorn smoke checks returned the expected app root, health, and metrics responses plus healer health, ready, and incidents responses. PyYAML parsed the Compose, monitoring, and workflow files; JSON and SVG assets parsed successfully. Bash and PowerShell scripts parsed, and the Windows renderer produced the expected default, staging, and production project filters. The GitHub Actions run for commit `0d20a75` passed lint and the secrets scan but failed during Linux test collection because the repository root was missing from pytest's import path. `pythonpath = ["."]` is the local fix and needs a commit/push and CI rerun. Compose/Prometheus validation, image builds, a live Docker incident demo, and remote deployment remain unverified until Docker and the external services are available; configuration files alone do not prove those outcomes.
