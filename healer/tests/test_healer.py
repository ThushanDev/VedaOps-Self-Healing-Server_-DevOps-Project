from dataclasses import replace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from healer import main as healer

client = TestClient(healer.app)


def setup_function() -> None:
    healer.ai_calls.clear()
    healer.restart_calls.clear()
    healer.history.clear()


def test_redacts_common_secret_formats() -> None:
    aws_key = "AKIA" + "A" * 16
    jwt_token = ".".join(("eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxMjMifQ", "A" * 16))
    original = (
        'password=hunter2 Bearer abc.def.ghi api_key: secret-value '
        'TELEGRAM_BOT_TOKEN=123456:abc-def {"password":"private phrase"} '
        f"aws={aws_key} jwt={jwt_token}"
    )
    safe = healer.redact(original)
    assert "hunter2" not in safe
    assert "abc.def.ghi" not in safe
    assert "secret-value" not in safe
    assert "123456:abc-def" not in safe
    assert "private phrase" not in safe
    assert aws_key not in safe
    assert jwt_token not in safe
    assert safe.count("[REDACTED]") == 7


def test_rate_limit_allows_only_configured_calls_per_minute() -> None:
    assert healer._rate_limited(now=1000) is False
    assert healer._rate_limited(now=1001) is True
    assert healer._rate_limited(now=1061) is False


def test_unknown_container_is_never_passed_to_ai_or_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = Mock()
    docker_api = Mock()
    monkeypatch.setattr(healer, "ask_ai", ai)
    monkeypatch.setattr(healer, "docker_client", docker_api)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "ContainerDown", "container": "db"}}]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "alerts_queued": 1}
    assert healer.history[0]["result"] == "container is not allowlisted"
    ai.assert_not_called()
    docker_api.containers.get.assert_not_called()


def test_unscoped_infrastructure_alert_requests_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(healer, "send_telegram", lambda _message: True)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "CAdvisorDown"}, "annotations": {"summary": "offline"}}]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "alerts_queued": 1}
    assert healer.history[0]["action"] == "notify_human"


def test_logical_app_label_maps_to_environment_container(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        healer,
        "settings",
        replace(
            healer.settings,
            target_container="vedaops-staging-app",
            allowed_containers=frozenset({"vedaops-staging-app"}),
        ),
    )
    logs = Mock(return_value="safe logs")
    monkeypatch.setattr(healer, "get_container_logs", logs)
    monkeypatch.setattr(
        healer,
        "ask_ai",
        lambda *_args: healer.Decision(cause="service healthy", action="ignore"),
    )
    monkeypatch.setattr(healer, "send_telegram", lambda _message: True)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "HighMemory", "container": "vedaops-app"}}]},
    )
    assert response.status_code == 200
    assert healer.history[0]["container"] == "vedaops-staging-app"
    logs.assert_called_once_with("vedaops-staging-app")


def test_ai_cause_is_sanitized_before_history_and_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(healer, "get_container_logs", lambda _name: "safe logs")
    monkeypatch.setattr(
        healer,
        "ask_ai",
        lambda *_args: healer.Decision(cause="token=should-not-leak", action="ignore"),
    )
    monkeypatch.setattr(healer, "send_telegram", lambda message: messages.append(message) is None)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "HighMemory", "container": "vedaops-app"}}]},
    )
    assert response.status_code == 200
    assert "should-not-leak" not in healer.history[0]["cause"]
    assert "should-not-leak" not in messages[0]


def test_multiple_alerts_are_processed_individually(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        healer,
        "ask_ai",
        lambda *_args: healer.Decision(cause="transient demo failure", action="ignore"),
    )
    monkeypatch.setattr(healer, "get_container_logs", lambda _name: "safe logs")
    monkeypatch.setattr(healer, "send_telegram", lambda _message: True)
    response = client.post(
        "/alert",
        json={
            "alerts": [
                {"labels": {"alertname": "ContainerDown", "container": "vedaops-app"}},
                {"labels": {"alertname": "HighMemory", "container": "vedaops-app"}},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "alerts_queued": 2}
    assert len(healer.history) == 2


def test_ai_json_is_validated_and_code_fence_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        content = [Mock(type="text", text='```json\n{"cause":"transient","action":"restart"}\n```')]

    fake_client = Mock()
    fake_client.messages.create.return_value = FakeResponse()
    monkeypatch.setattr(healer, "anthropic_client", fake_client)
    monkeypatch.setattr(healer, "_rate_limited", lambda: False)
    decision = healer.ask_ai("vedaops-app", "ContainerDown", "stopped", "logs")
    assert decision.action == "restart"


def test_restart_loop_guard_stops_restarts() -> None:
    assert healer._restart_limit_hit("vedaops-app", now=5000) is False
    assert healer._restart_limit_hit("vedaops-app", now=5001) is False
    assert healer._restart_limit_hit("vedaops-app", now=5002) is False
    assert healer._restart_limit_hit("vedaops-app", now=5003) is True


def test_ai_without_credentials_defaults_to_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(healer, "anthropic_client", None)
    decision = healer.ask_ai("vedaops-app", "ContainerDown", "stopped", "logs")
    assert decision.action == "notify_human"


def test_ai_error_falls_back_to_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(healer, "ask_ai", Mock(side_effect=ValueError("invalid JSON")))
    monkeypatch.setattr(healer, "get_container_logs", lambda _name: "safe logs")
    monkeypatch.setattr(healer, "send_telegram", lambda _message: True)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "ContainerDown", "container": "vedaops-app"}}]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "alerts_queued": 1}
    assert healer.history[0]["action"] == "notify_human"


def test_restart_is_restricted_to_container_down_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    docker_api = Mock()
    monkeypatch.setattr(
        healer,
        "ask_ai",
        lambda *_args: healer.Decision(cause="high memory", action="restart"),
    )
    monkeypatch.setattr(healer, "get_container_logs", lambda _name: "safe logs")
    monkeypatch.setattr(healer, "docker_client", docker_api)
    monkeypatch.setattr(healer, "send_telegram", lambda _message: True)
    response = client.post(
        "/alert",
        json={"alerts": [{"labels": {"alertname": "HighMemory", "container": "vedaops-app"}}]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted", "alerts_queued": 1}
    assert healer.history[0]["action"] == "notify_human"
    docker_api.containers.get.assert_not_called()
