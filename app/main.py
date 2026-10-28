"""Small instrumented HTTP service used by the VedaOps demo."""

import hmac
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="VedaOps", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
REQUESTS = Counter(
    "vedaops_http_requests_total",
    "HTTP requests handled by the demo service.",
    ("method", "path", "status"),
)
REQUEST_DURATION = Histogram(
    "vedaops_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    with REQUEST_DURATION.labels(request.method, request.url.path).time():
        response = await call_next(request)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    return response


@app.get("/", response_model=None)
def root(request: Request) -> dict[str, str] | HTMLResponse:
    if "text/html" in request.headers.get("accept", ""):
        return dashboard()
    return {"service": "VedaOps", "tagline": "Diagnose. Heal. Tell you.", "status": "running"}


def dashboard() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8"))


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page() -> HTMLResponse:
    return dashboard()


async def healer_request(path: str, *, method: str = "GET") -> httpx.Response:
    base_url = os.getenv("HEALER_URL", "").rstrip("/")
    if not base_url:
        raise HTTPException(status_code=503, detail="Docker healer is not connected to this hosted app.")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.request(method, f"{base_url}{path}")
        if response.is_error:
            raise HTTPException(
                status_code=response.status_code,
                detail="Healer could not complete the request.",
            )
        return response
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Docker healer is temporarily unavailable.") from exc


@app.get("/api/dashboard")
async def dashboard_data() -> dict:
    try:
        containers_response = await healer_request("/containers")
        incidents_response = await healer_request("/incidents")
    except HTTPException as exc:
        if exc.status_code == 503:
            return {
                "docker_connected": False,
                "message": exc.detail,
                "containers": [],
                "incidents": [],
                "actions_enabled": False,
            }
        raise
    return {
        "docker_connected": True,
        "message": "Docker host connected",
        "containers": containers_response.json(),
        "incidents": incidents_response.json(),
        "actions_enabled": bool(os.getenv("DASHBOARD_ACTION_TOKEN", "").strip()),
    }


@app.get("/api/containers/{name}/logs")
async def container_logs(name: str) -> dict:
    response = await healer_request(f"/containers/{name}/logs")
    return response.json()


@app.post("/api/actions/restart/{name}")
async def restart_container(name: str, request: Request) -> dict:
    action_token = os.getenv("DASHBOARD_ACTION_TOKEN", "").strip()
    if not action_token:
        raise HTTPException(status_code=503, detail="Dashboard actions are not configured.")
    if not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {action_token}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return (await healer_request(f"/actions/restart/{name}", method="POST")).json()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    bearer_token = os.getenv("METRICS_BEARER_TOKEN", "").strip()
    if bearer_token and not hmac.compare_digest(
        request.headers.get("authorization", ""), f"Bearer {bearer_token}"
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
