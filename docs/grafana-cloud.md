# Free hosted Grafana dashboard

Grafana Cloud hosts the VedaOps dashboard on its always-free plan. Prometheus
continues to scrape the local Compose stack and sends metrics to Grafana Cloud
over HTTPS. The optional `grafana-cloud` Compose profile is off by default.
The free plan currently includes up to 10,000 active metric series and 14 days
of retention; check Grafana's current [plan limits](https://grafana.com/pricing/)
before adding more monitored services.

## Set up the free stack

1. Create a Grafana Cloud Free account and open its Cloud Portal. Create or
   select a stack, then open the Prometheus Metrics details. Copy its remote
   write endpoint and instance ID. Grafana documents these values in its
   [Prometheus remote-write guide](https://grafana.com/docs/grafana-cloud/send-data/metrics/metrics-prometheus/).
2. Create a Cloud Access Policy token with the `metrics:write` scope. Treat it
   as a password. Do not put it in Git, a command, or a chat message.
3. Copy `.env.example` to `.env`. Set `GRAFANA_CLOUD_PROMETHEUS_URL` to the
   HTTPS endpoint ending in `/api/prom/push`, and set
   `GRAFANA_CLOUD_PROMETHEUS_USERNAME` to the Prometheus instance ID.
4. Create `.secrets/grafana_cloud_token` and save the token as its only line.
   Both `.env` and `.secrets/` are ignored by Git. Keep the token private.
5. From the repository root, render the optional Prometheus config and start
   the forwarding service:

   ```powershell
   python scripts/render-grafana-cloud-config.py
   docker compose --profile grafana-cloud up -d prometheus-cloud
   ```

   The cloud profile uses the existing internal scrape targets and an outbound
   network for HTTPS remote write. It does not publish a Prometheus port.
6. Create the importable dashboard file:

   ```powershell
   python scripts/export-grafana-cloud-dashboard.py
   ```

7. In Grafana Cloud, choose **Dashboards → New → Import dashboard**, upload
   `monitoring/grafana/dashboards/vedaops-overview-cloud.json`, select the
   Grafana Cloud Prometheus data source, and import it. The dashboard is only
   visible to signed-in users unless you explicitly change its sharing settings.

The dashboard shows data only while the monitored Compose stack is running and
Prometheus can reach Grafana Cloud. On a free laptop setup, sleep, shutdown, or
loss of internet pauses new metrics; previously received metrics remain subject
to the plan's retention limit. No VPS or paid hosting is required.

## Stop forwarding

```powershell
docker compose --profile grafana-cloud stop prometheus-cloud
```

To revoke access, delete or rotate the token in Grafana Cloud, then replace the
local ignored token file. The standard local Grafana, Prometheus, and alerting
services continue to work without this profile.
