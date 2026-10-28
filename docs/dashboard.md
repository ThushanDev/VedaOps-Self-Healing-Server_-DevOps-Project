# VedaOps web dashboard

The app serves the responsive VedaOps dashboard at `/` and `/dashboard`. Its JSON service identity remains available to non-browser clients at `/` when they request JSON (or send the default `*/*` Accept header).

## Run with Docker Compose

Start the stack with `docker compose up --build -d`, then open `http://localhost:8080`. The web app talks to the healer over the private Compose network. The healer lists containers only when they carry the configured Compose project label (`vedaops` by default), and exposes logs only for those managed containers. Restart actions also require the existing container allowlist and hourly restart limit.

Restart buttons are disabled unless `DASHBOARD_ACTION_TOKEN` is configured. Create a private `.env` file from `.env.example`, set a random token, and restart the app and healer. For example, in PowerShell:

```powershell
$token = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
Add-Content .env "DASHBOARD_ACTION_TOKEN=$token"
```

Keep `.env` private. The dashboard asks for this token in the browser when a restart is requested; it is held in page memory only. The server checks it before forwarding a request, and the healer checks both its allowlist and restart rate limit before taking action.

## Hosted serverless deployments

Free serverless hosts such as Render or Vercel do not have access to the Docker daemon on a developer's machine. On those hosts the dashboard still loads, but shows an explicit disconnected state and does not invent container data or offer restart actions. To show live data, run the app and healer together on a Docker host using Compose. Do not expose the healer's private API directly to the internet.

The current health distribution is a live snapshot. Historical health charts require a time-series source and are labeled as unavailable until monitoring history is connected.
