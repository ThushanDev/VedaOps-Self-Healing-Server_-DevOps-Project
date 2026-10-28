from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_describes_service() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "VedaOps",
        "tagline": "Diagnose. Heal. Tell you.",
        "status": "running",
    }


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_exports_request_counter() -> None:
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "vedaops_http_requests_total" in response.text
