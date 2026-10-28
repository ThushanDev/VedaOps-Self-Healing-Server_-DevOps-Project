"""Small instrumented HTTP service used by the VedaOps demo."""

import hmac
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = FastAPI(title="VedaOps", version="1.0.0")
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


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "VedaOps", "tagline": "Diagnose. Heal. Tell you.", "status": "running"}


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
