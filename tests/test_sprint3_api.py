import asyncio
import time
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_api import readiness_clients
from test_frontend import click, dashboard


@pytest.mark.parametrize(
    "risk,message_id,attempted,dispatched",
    [("HIGH", "unexpected-id", False, False),
     ("CRITICAL", "published-id", True, True),
     ("CRITICAL", "", True, False)],
)
def test_alert_attempted_and_dispatched_match_actual_persisted_publish_outcome(
    api_environment, sample_png_bytes, risk, message_id, attempted, dispatched
):
    main, analyzer, climate, publisher, firestore = api_environment
    analyzer.return_value.update(
        risk_level=risk, hvi_score=6.0 if risk == "HIGH" else 8.0,
        alert_attempted=True, alert_dispatched=True,
    )
    publisher.return_value = message_id
    response = TestClient(main.app).post(
        "/api/analyze", files={"file": ("district.png", sample_png_bytes, "image/png")}
    )
    assert response.status_code == 200
    stored = firestore.collection.return_value.document.return_value.set.call_args.args[0]
    for report in (stored, response.json()):
        assert report["alert_attempted"] is attempted
        assert report["alert_dispatched"] is dispatched
    assert publisher.call_count == int(attempted)
    if attempted:
        assert publisher.call_args.args[0]["zone_id"] == stored["zone_id"]


@pytest.mark.parametrize(
    "mime,payload",
    [("image/jpeg", b"not an image"), ("image/png", b"not an image"),
     ("image/jpeg", b""), ("image/png", b""),
     ("image/jpeg", b"\x89PNG\r\n\x1a\n"), ("image/png", b"\xff\xd8\xff")],
)
def test_magic_bytes_and_empty_uploads_are_rejected_before_any_cloud_call(
    api_environment, mime, payload
):
    main, analyzer, climate, publisher, firestore = api_environment
    response = TestClient(main.app).post(
        "/api/analyze", files={"file": ("private-filename.jpeg", payload, mime)}
    )
    assert response.status_code == 415
    assert set(response.json()) == {"code", "message"}
    assert "private-filename" not in response.text
    analyzer.assert_not_called()
    climate.assert_not_called()
    publisher.assert_not_called()
    firestore.collection.assert_not_called()


@pytest.mark.parametrize("status", [413, 415, 422, 502, 503, 500])
def test_all_api_failures_use_one_sanitized_code_message_envelope(
    api_environment, sample_png_bytes, status, caplog
):
    main, analyzer, climate, publisher, firestore = api_environment
    secret = "Traceback RAW-CLOUD-PAYLOAD projects/private Bearer qa-secret private-filename.png"
    payload = sample_png_bytes
    if status == 413:
        payload = b"x" * (main.MAX_UPLOAD_BYTES + 1)
    elif status == 415:
        payload = b"invalid"
    elif status == 502:
        analyzer.side_effect = main.VisionAnalysisError(secret)
    elif status == 503:
        firestore.collection.side_effect = main.DatabaseError(secret)
    elif status == 500:
        analyzer.side_effect = RuntimeError(secret)
    client = TestClient(main.app, raise_server_exceptions=False)
    response = client.post("/api/analyze") if status == 422 else client.post(
        "/api/analyze", files={"file": ("private-filename.png", payload, "image/png")}
    )
    assert response.status_code == status
    assert set(response.json()) == {"code", "message"}
    assert all(isinstance(value, str) and value for value in response.json().values())
    for forbidden in ("Traceback", "RAW-CLOUD-PAYLOAD", "projects/private", "qa-secret", "private-filename"):
        assert forbidden not in response.text
        assert forbidden not in caplog.text


def test_readiness_enforces_4_5_second_deadline_and_marks_timeouts_unavailable(
    api_environment, monkeypatch
):
    main = api_environment[0]
    observed = []
    probe = Mock(side_effect=AssertionError("A timed-out worker must not be executed here"))
    monkeypatch.setattr(main, "check_dependency", probe)

    async def expire(awaitable, timeout):
        observed.append(timeout)
        awaitable.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(main.asyncio, "wait_for", expire)
    response = TestClient(main.app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dependencies"] == {name: "unavailable" for name in main.DEPENDENCIES}
    assert observed == [4.5] * 4
    probe.assert_not_called()


def test_malformed_analysis_cannot_return_http_200(api_environment, sample_png_bytes):
    main, analyzer, climate, publisher, firestore = api_environment
    analyzer.return_value.pop("zone_id")
    response = TestClient(main.app, raise_server_exceptions=False).post(
        "/api/analyze", files={"file": ("district.png", sample_png_bytes, "image/png")}
    )
    assert response.status_code == 500
    assert set(response.json()) == {"code", "message"}


def test_readiness_real_elapsed_deadline_is_4_5_seconds_without_worker_shutdown_delay(api_environment, monkeypatch):
    main = api_environment[0]

    async def blocked_worker(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(main.asyncio, "to_thread", blocked_worker)
    started = time.monotonic()
    response = asyncio.run(main.health_check())
    elapsed = time.monotonic() - started
    assert 4.4 <= elapsed < 5.0, elapsed
    assert response["status"] == "degraded"
    assert response["dependencies"] == {name: "unavailable" for name in main.DEPENDENCIES}


def test_readiness_never_returns_credentials_or_raw_dependency_failures(api_environment, readiness_clients):
    secret = "RAW-CLOUD-PAYLOAD projects/private Bearer qa-secret Traceback"
    probes = [readiness_clients["gemini"].models.get,
              readiness_clients["firestore"].collection.return_value.limit.return_value.get,
              readiness_clients["pubsub"].get_topic, readiness_clients["bigquery"].query]
    for probe in probes:
        probe.side_effect = RuntimeError(secret)
    response = TestClient(api_environment[0].app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    for forbidden in ("RAW-CLOUD-PAYLOAD", "projects/private", "qa-secret", "Traceback"):
        assert forbidden not in response.text


def test_offline_api_report_renders_current_dashboard_fields_without_none_metrics(api_environment, sample_png_bytes, dashboard):
    response = TestClient(api_environment[0].app).post(
        "/api/analyze", files={"file": ("district.png", sample_png_bytes, "image/png")}
    )
    assert response.status_code == 200
    dashboard[1].return_value = response
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert not app.exception
    assert len(app.metric) == 7
    assert all(metric.value not in {"None", "-"} for metric in app.metric)
    assert any("Published successfully" in element.value for element in app.error)
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["alert_attempted"] is True
    assert stored["alert_dispatched"] is True
    api_environment[1].assert_awaited_once()