(() => {
  const $ = (id) => document.getElementById(id);
  let state = { docker_connected: false, containers: [], incidents: [], actions_enabled: false };
  const setText = (id, value) => { $(id).textContent = value; };
  const timeLabel = (value) => {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
  const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

  function render() {
    const items = state.containers || [];
    const healthy = items.filter((item) => item.status === "healthy").length;
    const warning = items.filter((item) => item.status === "warning").length;
    const down = items.filter((item) => item.status === "down").length;
    const total = items.length;
    const connected = state.docker_connected;
    $("health-dot").style.background = connected ? "var(--green)" : "var(--yellow)";
    setText("system-label", connected ? (down ? "Attention needed" : "System healthy") : "Docker disconnected");
    $("connection-banner").classList.toggle("hidden", connected);
    if (!connected) setText("connection-message", state.message || "Container data appears when VedaOps runs with Docker Compose.");
    setText("total-count", connected ? total : "—");
    setText("healthy-count", connected ? healthy : "—");
    setText("warning-count", connected ? warning : "—");
    setText("down-count", connected ? down : "—");
    setText("running-copy", connected ? `${items.filter((item) => item.state === "running").length} running · ${down} stopped` : "Waiting for Docker data");
    setText("healthy-percent", connected ? `${total ? Math.round(healthy / total * 100) : 0}% of total` : "—");
    setText("donut-total", connected ? total : "—");
    setText("legend-healthy", connected ? healthy : "—");
    setText("legend-warning", connected ? warning : "—");
    setText("legend-down", connected ? down : "—");
    const donut = $("donut");
    donut.style.setProperty("--healthy", `${total ? healthy / total * 100 : 0}%`);
    donut.style.setProperty("--warning", `${total ? warning / total * 100 : 0}%`);
    $("health-chart").classList.toggle("has-snapshot", connected && total > 0);
    $("health-chart").innerHTML = connected && total ? `<div class="health-snapshot"><span class="snapshot-label">LIVE SNAPSHOT · ${total} CONTAINER${total === 1 ? "" : "S"}</span><div class="health-track"><i class="track-healthy" style="width:${healthy / total * 100}%"></i><i class="track-warning" style="width:${warning / total * 100}%"></i><i class="track-down" style="width:${down / total * 100}%"></i></div><div class="snapshot-counts"><span><i class="green-dot"></i>${healthy} healthy</span><span><i class="yellow-dot"></i>${warning} warning</span><span><i class="red-dot"></i>${down} down</span></div><small>Historical trend starts collecting when monitoring history is connected.</small></div>` : `<div class="empty-chart"><span class="chart-glyph">⌁</span><strong>${connected ? "No managed containers found" : "Waiting for live container data"}</strong><span>${connected ? "Start the VedaOps Compose stack to populate this overview." : "Connect this service to the Docker healer to see health changes here."}</span></div>`;
    $("container-subtitle").textContent = connected ? `${total} managed container${total === 1 ? "" : "s"} in your VedaOps stack` : "Managed containers in your VedaOps stack";
    $("container-rows").innerHTML = connected && total ? items.map((item) => {
      const status = ["healthy", "warning", "down"].includes(item.status) ? item.status : "down";
      const action = state.actions_enabled && item.restart_allowed ? `<button class="row-action restart-action" data-name="${safe(item.name)}">Restart</button>` : "";
      return `<tr><td><strong>${safe(item.name)}</strong></td><td><span class="status-badge ${status}">${safe(status)}</span></td><td>${safe(item.restarts)}</td><td title="${safe(item.image)}">${safe(item.image)}</td><td><button class="row-action logs-action" data-name="${safe(item.name)}">Logs</button>${action}</td></tr>`;
    }).join("") : `<tr><td class="empty-row" colspan="5">${connected ? "No containers were found in this Compose project." : "Container data will appear when the Docker host is connected."}</td></tr>`;
    const incidents = [...(state.incidents || [])].reverse().slice(0, 6);
    $("activity-list").innerHTML = incidents.length ? incidents.map((item) => `<div class="activity-item"><i class="activity-marker ${item.action === "restart" && /fail|limit|review/i.test(item.result || "") ? "down" : ""}"></i><div><strong>${safe(item.alert || item.action || "Incident")}: ${safe(item.container || "system")}</strong><p>${safe(item.cause || item.result || "Event recorded")}</p><p>Action: ${safe(item.action || "unknown")} · ${safe(item.result || "")}</p></div><time>${safe(timeLabel(item.timestamp))}</time></div>`).join("") : `<div class="activity-empty"><span>◷</span><p>No incidents recorded yet.</p><small>New alert and recovery events will show here.</small></div>`;
    $("action-note").textContent = state.actions_enabled ? "Restart is available only for the configured allowlisted app container. The healer also enforces its hourly restart limit." : "Restart actions are available only in a configured, connected Docker Compose deployment.";
    $("token-entry").classList.toggle("hidden", !state.actions_enabled);
    bindActions();
  }

  async function load() {
    $("refresh").disabled = true;
    try {
      const response = await fetch("/api/dashboard", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
      state = await response.json();
      render();
    } catch (error) {
      state = { docker_connected: false, containers: [], incidents: [], actions_enabled: false, message: error.message };
      render();
    } finally { $("refresh").disabled = false; }
  }

  function bindActions() {
    document.querySelectorAll(".logs-action").forEach((button) => button.addEventListener("click", async () => {
      const name = button.dataset.name;
      $("logs-title").textContent = name;
      $("logs-content").textContent = "Loading logs…";
      $("logs-dialog").showModal();
      try {
        const response = await fetch(`/api/containers/${encodeURIComponent(name)}/logs`, { cache: "no-store" });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Could not load container logs.");
        $("logs-content").textContent = result.logs || "No logs available.";
      } catch (error) { $("logs-content").textContent = error.message; }
    }));
    document.querySelectorAll(".restart-action").forEach((button) => button.addEventListener("click", async () => {
      if (!window.confirm(`Restart ${button.dataset.name}? This will briefly interrupt that container.`)) return;
      button.disabled = true;
      try {
        const token = $("action-token").value.trim();
        const response = await fetch(`/api/actions/restart/${encodeURIComponent(button.dataset.name)}`, {
          method: "POST", headers: { Authorization: `Bearer ${token}` },
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Restart request failed.");
        window.alert(result.result || "Restart request completed.");
        await load();
      } catch (error) { window.alert(error.message); }
      finally { button.disabled = false; }
    }));
  }

  $("clock").textContent = new Intl.DateTimeFormat([], { dateStyle: "medium", timeStyle: "short" }).format(new Date());
  $("refresh").addEventListener("click", load);
  $("close-logs").addEventListener("click", () => $("logs-dialog").close());
  load();
  window.setInterval(load, 30000);
})();
