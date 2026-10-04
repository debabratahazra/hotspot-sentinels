import asyncio
import copy
import importlib
import json
import subprocess
from datetime import timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.testclient import TestClient
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from google.api_core.exceptions import GoogleAPIError
from PIL import Image
from pydantic import create_model


@pytest.fixture
def readiness_clients(monkeypatch):
    import main

    clients = {name: Mock() for name in main.DEPENDENCIES}
    clients["pubsub"].topic_path.return_value = "projects/qa/topics/alerts"
    monkeypatch.setattr(main.vision_analyzer, "get_client", lambda: clients["gemini"])
    monkeypatch.setattr(main.database, "get_db", lambda: clients["firestore"])
    monkeypatch.setattr(main.alert_dispatcher, "_get_client", lambda: clients["pubsub"])
    monkeypatch.setattr(main.climate_service, "_get_client", lambda: clients["bigquery"])
    return clients


def upload(environment, image):
    return TestClient(environment[0].app).post("/api/analyze", files={"file": ("district.png", image, "image/png")})


@pytest.fixture
def historical_scan_records(valid_report):
    """Schema-era examples shared by history, strict-analysis, and regression tests."""
    current = copy.deepcopy(valid_report)
    current.update(climate_source="bigquery", alert_attempted=True, doc_id="current-scan-id")
    records = {
        name: copy.deepcopy(current) for name in (
            "broken_era", "missing_envelope", "invalid_surface_total",
            "contradictory_risk", "firestore_timestamp", "retired_extra_field",
        )
    }
    for field in ("zone_id", "coordinates", "alert_dispatched"):
        del records["broken_era"][field]
    for field in ("climate_source", "alert_attempted", "doc_id"):
        del records["missing_envelope"][field]
    records["invalid_surface_total"]["surface_breakdown"]["asphalt_pct"] = 54
    records["contradictory_risk"]["risk_level"] = "LOW"
    records["firestore_timestamp"]["timestamp"] = DatetimeWithNanoseconds(
        2025, 6, 1, 12, 0, 0, nanosecond=123456789, tzinfo=timezone.utc
    )
    records["retired_extra_field"]["legacy_cooling_strategy"] = {
        "schema_version": 0, "shade_priority": ["west_roofs", "bus_stops"],
    }
    records["current"] = current
    return records


@pytest.fixture
def history_documents(api_environment):
    def install(records):
        documents = [Mock(to_dict=Mock(return_value=copy.deepcopy(record))) for record in records]
        query = api_environment[4].collection.return_value.order_by.return_value.limit.return_value
        query.stream.return_value = documents
        return documents

    return install


def assert_history_preserves_records(api_environment, history_documents, records):
    documents = history_documents(records)
    response = TestClient(api_environment[0].app, raise_server_exceptions=False).get("/api/scans")
    assert response.status_code == 200, response.text
    expected = copy.deepcopy(records)
    for record in expected:
        if isinstance(record.get("timestamp"), DatetimeWithNanoseconds):
            record["timestamp"] = record["timestamp"].isoformat()
    assert response.json() == {"scans": expected}
    for document in documents:
        document.to_dict.assert_called_once_with()
    api_environment[1].assert_not_called()
    api_environment[2].assert_not_called()
    api_environment[3].assert_not_called()


def test_scans_preserves_broken_era_rows_missing_canonical_fields(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["broken_era"]])


def test_scans_preserves_rows_written_before_application_envelope(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["missing_envelope"]])


def test_scans_preserves_legacy_surface_percentages_not_totalling_100(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["invalid_surface_total"]])


def test_scans_preserves_legacy_risk_band_contradicting_hvi(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["contradictory_risk"]])


def test_scans_serializes_firestore_nanosecond_timestamps(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["firestore_timestamp"]])


def test_scans_preserves_unknown_fields_from_retired_schema(api_environment, history_documents, historical_scan_records):
    assert_history_preserves_records(api_environment, history_documents, [historical_scan_records["retired_extra_field"]])


def test_scans_one_bad_historical_row_cannot_fail_or_drop_current_rows(api_environment, history_documents, historical_scan_records):
    current = historical_scan_records["current"]
    records = [current, *[record for name, record in historical_scan_records.items() if name != "current"], current]
    assert_history_preserves_records(api_environment, history_documents, records)


@pytest.mark.parametrize("field,value,error_location", [
    ("zone_id", None, ("response", "zone_id")),
    ("coordinates", None, ("response", "coordinates")),
    ("hvi_score", "8.0", ("response", "hvi_score")),
    ("surface_breakdown", {"asphalt_pct": 101, "dark_roof_pct": 0, "concrete_pct": 0, "green_canopy_pct": 0},
     ("response", "surface_breakdown", "asphalt_pct")),
])
def test_analyze_strict_response_rejects_malformed_fresh_reports(api_environment, sample_png_bytes, historical_scan_records, field, value, error_location):
    main = api_environment[0]
    route = next(route for route in main.app.routes if route.path == "/api/analyze")
    assert route.response_model is main.AnalysisResponse
    report = copy.deepcopy(historical_scan_records["current"])
    if value is None:
        del report[field]
    else:
        report[field] = value
    api_environment[1].return_value = report
    with pytest.raises(ResponseValidationError) as rejected:
        upload(api_environment, sample_png_bytes)
    assert error_location in {tuple(error["loc"]) for error in rejected.value.errors()}
    api_environment[1].assert_awaited_once()


@pytest.mark.parametrize("mixed", [False, True], ids=["legacy-only", "mixed-current-and-legacy"])
def test_old_strict_history_response_rejects_legacy_rows_and_entire_mixed_response(api_environment, history_documents, historical_scan_records, mixed):
    main = api_environment[0]
    strict_history = create_model("OldStrictScanHistoryResponse", scans=(list[main.AnalysisResponse], ...))
    old_app = FastAPI()
    old_app.add_api_route("/api/scans", main.get_scans, response_model=strict_history)
    records = [historical_scan_records["broken_era"]]
    if mixed:
        records.insert(0, historical_scan_records["current"])
    history_documents(records)
    with pytest.raises(ResponseValidationError) as rejected:
        TestClient(old_app).get("/api/scans")
    errors = rejected.value.errors()
    assert {tuple(error["loc"]) for error in errors} == {
        ("response", "scans", int(mixed), field)
        for field in ("zone_id", "coordinates", "alert_dispatched")
    }
    response = TestClient(old_app, raise_server_exceptions=False).get("/api/scans")
    assert response.status_code == 500
    print(f"old strict history: {'mixed' if mixed else 'legacy-only'} -> HTTP {response.status_code}; "
          f"rejected locations={[error['loc'] for error in errors]}")


@pytest.mark.parametrize("image_format,content_type", [("JPEG", "image/jpeg"), ("PNG", "image/png")], ids=["jpeg", "png"])
def test_analyze_awaits_analyzer_and_returns_contract_valid_dict(api_environment, tmp_path, image_format, content_type):
    image = BytesIO()
    Image.new("RGB", (8, 8), (40, 120, 50)).save(image, format=image_format)
    image_bytes = image.getvalue()
    filename = f"district.{image_format.lower()}"
    response = TestClient(api_environment[0].app).post("/api/analyze", files={"file": (filename, image_bytes, content_type)})
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert not asyncio.iscoroutine(response.json())
    api_environment[1].assert_awaited_once()
    arguments = api_environment[1].await_args.kwargs
    assert arguments["image_bytes"] == image_bytes
    assert arguments["ambient_temp"] == 38.5
    assert arguments["zone_name"] is None
    assert response.json()["zone_name"] == api_environment[1].return_value["zone_name"]
    assert arguments["mime_type"] == content_type
    report_path = tmp_path / "analyze.json"
    report_path.write_text(json.dumps(response.json()))
    result = subprocess.run(["python3", ".github/skills/heat-report-validation/scripts/validate_report.py", str(report_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_testclient_response_is_dict_not_coroutine(api_environment, sample_png_bytes):
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert not asyncio.iscoroutine(response.json())
    assert response.json()["zone_id"] == "qa-zone"
    api_environment[1].assert_awaited_once()


@pytest.mark.parametrize("fields,expected_identity,expected_source", [
    ({"zone_id": " caller-zone ", "zone_name": " Caller district ",
      "lat": "12.5", "lng": "-45.25"},
     {"zone_id": " caller-zone ", "zone_name": " Caller district ",
      "coordinates": {"lat": 12.5, "lng": -45.25}},
     {"zone_id": "supplied", "zone_name": "supplied",
      "coordinates": {"lat": "supplied", "lng": "supplied"}}),
    ({}, {"zone_id": "qa-zone", "zone_name": "QA District",
          "coordinates": {"lat": 1.3521, "lng": 103.8198}},
     {"zone_id": "inferred", "zone_name": "inferred",
      "coordinates": {"lat": "inferred", "lng": "inferred"}}),
    ({"zone_id": "caller-zone", "lat": "12.5"},
     {"zone_id": "caller-zone", "zone_name": "QA District",
      "coordinates": {"lat": 12.5, "lng": 103.8198}},
     {"zone_id": "supplied", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "inferred"}}),
    ({"zone_name": "Caller district", "lng": "-45.25"},
     {"zone_id": "qa-zone", "zone_name": "Caller district",
      "coordinates": {"lat": 1.3521, "lng": -45.25}},
     {"zone_id": "inferred", "zone_name": "supplied",
      "coordinates": {"lat": "inferred", "lng": "supplied"}}),
    ({"lat": "12.5"},
     {"zone_id": "qa-zone", "zone_name": "QA District",
      "coordinates": {"lat": 12.5, "lng": 103.8198}},
     {"zone_id": "inferred", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "inferred"}}),
    ({"lat": "90", "lng": "-180"},
     {"zone_id": "qa-zone", "zone_name": "QA District",
      "coordinates": {"lat": 90.0, "lng": -180.0}},
     {"zone_id": "inferred", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "supplied"}}),
    ({"lat": "-90", "lng": "180"},
     {"zone_id": "qa-zone", "zone_name": "QA District",
      "coordinates": {"lat": -90.0, "lng": 180.0}},
     {"zone_id": "inferred", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "supplied"}}),
], ids=["all-supplied", "all-inferred", "mixed-lat", "mixed-lng",
        "lat-only", "upper-lat-lower-lng", "lower-lat-upper-lng"])
def test_analyze_identity_and_provenance_reach_response_and_firestore(
    api_environment, sample_png_bytes, valid_report, monkeypatch,
    fields, expected_identity, expected_source,
):
    main, _, climate, dispatch, firestore = api_environment
    model_client = Mock()
    model_client.models.generate_content.return_value.text = json.dumps(valid_report)
    monkeypatch.setattr(main.vision_analyzer, "get_client", lambda: model_client)
    analyzer = AsyncMock(wraps=main.vision_analyzer.analyze_urban_hotspot)
    monkeypatch.setattr(main, "analyze_urban_hotspot", analyzer)
    response = TestClient(main.app).post(
        "/api/analyze", data={"ambient_temp_c": "37.0", **fields},
        files={"file": ("not-a-zone.png", sample_png_bytes, "image/png")},
    )
    assert response.status_code == 200, response.text
    document = firestore.collection.return_value.document.return_value
    document.set.assert_called_once()
    stored = document.set.call_args.args[0]
    for report in (response.json(), stored):
        for field, expected in expected_identity.items():
            assert report[field] == expected
        assert report["identity_source"] == expected_source
        assert report["ambient_temp_c"] == 37.0
        assert report["climate_source"] == "caller"
    analyzer.assert_awaited_once()
    arguments = analyzer.await_args.kwargs
    assert arguments["zone_id"] == fields.get("zone_id")
    assert arguments["zone_name"] == fields.get("zone_name")
    assert arguments["coordinates"] == (
        {key: float(fields[key]) for key in ("lat", "lng") if key in fields} or None
    )
    assert arguments["mime_type"] == "image/png"
    climate.assert_not_called()
    model_client.models.generate_content.assert_called_once()
    dispatch.assert_called_once()


@pytest.mark.parametrize("fields", [
    {"lat": "91"}, {"lat": "-91"}, {"lng": "181"}, {"lng": "-181"},
    {"lat": "not-a-number"}, {"lng": "not-a-number"},
    {"lat": "nan"}, {"lat": "inf"}, {"lng": "-inf"},
    {"zone_id": ""}, {"zone_id": "   "}, {"zone_name": ""},
    {"zone_name": " \t "}, {"lat": " "}, {"lng": ""},
], ids=["lat-above", "lat-below", "lng-above", "lng-below",
        "lat-nonnumeric", "lng-nonnumeric", "lat-nan", "lat-infinity",
        "lng-infinity", "id-empty", "id-whitespace", "name-empty",
        "name-whitespace", "lat-blank", "lng-blank"])
def test_invalid_identity_returns_standard_422_before_any_cloud_calls(
    api_environment, sample_png_bytes, fields,
):
    main, analyzer, climate, dispatch, firestore = api_environment
    response = TestClient(main.app).post(
        "/api/analyze", data=fields,
        files={"file": ("district.png", sample_png_bytes, "image/png")},
    )
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}
    assert isinstance(response.json()["code"], str)
    assert response.json()["code"]
    assert isinstance(response.json()["message"], str)
    assert response.json()["message"]
    analyzer.assert_not_called()
    climate.assert_not_called()
    dispatch.assert_not_called()
    assert firestore.mock_calls == []


def test_legacy_analysis_response_does_not_invent_identity_provenance(api_environment, sample_png_bytes):
    assert "identity_source" not in api_environment[1].return_value
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    assert "identity_source" not in response.json()


def test_synchronous_climate_database_and_dispatch_use_to_thread(api_environment, sample_png_bytes, monkeypatch):
    main = api_environment[0]
    original = asyncio.to_thread
    calls = []

    async def tracked_to_thread(function, *args, **kwargs):
        calls.append(function)
        return await original(function, *args, **kwargs)

    monkeypatch.setattr(main.asyncio, "to_thread", tracked_to_thread)
    assert upload(api_environment, sample_png_bytes).status_code == 200
    assert calls == [main.get_latest_temperature, main.trigger_alert_if_critical, main.save_hotspot_report]
    api_environment[3].assert_called_once()


def test_critical_report_triggers_dispatch_at_eight_boundary(api_environment, sample_png_bytes):
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    api_environment[3].assert_called_once()
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["hvi_score"] == 8.0
    assert stored["alert_dispatched"] is True


@pytest.mark.parametrize("score,band", [(4.0, "MODERATE"), (6.0, "HIGH"), (7.9, "HIGH")])
def test_high_and_noncritical_reports_never_dispatch_or_preserve_untrusted_true(api_environment, sample_png_bytes, score, band):
    api_environment[1].return_value.update(hvi_score=score, risk_level=band, alert_dispatched=True)
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    api_environment[3].assert_not_called()
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["alert_dispatched"] is False
    assert response.json()["alert_dispatched"] is False


@pytest.mark.parametrize("message_id,expected", [("published-message-id", True), ("", False)])
def test_alert_dispatched_is_stored_true_only_after_successful_publish(api_environment, sample_png_bytes, message_id, expected):
    api_environment[3].return_value = message_id
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    document = api_environment[4].collection.return_value.document.return_value
    document.set.assert_called_once()
    assert document.set.call_args.args[0]["alert_dispatched"] is expected
    assert response.json()["alert_dispatched"] is expected


@pytest.mark.parametrize("source", ["bigquery", "fallback"])
def test_climate_source_round_trips_to_response_and_firestore(api_environment, sample_png_bytes, source):
    api_environment[2].return_value["source"] = source
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    assert response.json()["climate_source"] == source
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["climate_source"] == source


@pytest.mark.parametrize("limit,expected", [(0, 1), (-5, 1), (10000, 100)])
def test_scans_clamps_limits_through_real_database_helper(api_environment, limit, expected):
    response = TestClient(api_environment[0].app).get("/api/scans", params={"limit": limit})
    assert response.status_code == 200
    assert response.json() == {"scans": []}
    query = api_environment[4].collection.return_value.order_by.return_value
    query.limit.assert_called_once_with(expected)


@pytest.mark.parametrize("value", ["ten", "1.5"])
def test_scans_rejects_noninteger_limits_before_firestore(api_environment, value):
    response = TestClient(api_environment[0].app).get("/api/scans", params={"limit": value})
    assert response.status_code == 422
    api_environment[4].collection.assert_not_called()


@pytest.mark.parametrize("operation,expected", [("vision", 502), ("write", 503), ("read", 503)])
def test_service_errors_map_status_without_secrets_in_response_or_logs(api_environment, sample_png_bytes, caplog, operation, expected):
    main = api_environment[0]
    secret = "RAW-CLOUD-PAYLOAD Bearer qa-secret projects/private/buckets/private Traceback"
    if operation == "vision":
        api_environment[1].side_effect = main.VisionAnalysisError(secret)
    elif operation == "write":
        api_environment[4].collection.return_value.document.return_value.set.side_effect = GoogleAPIError(secret)
    else:
        api_environment[4].collection.return_value.order_by.return_value.limit.return_value.stream.side_effect = GoogleAPIError(secret)
    response = TestClient(main.app).get("/api/scans") if operation == "read" else upload(api_environment, sample_png_bytes)
    assert response.status_code == expected
    for text in (response.text, caplog.text):
        for forbidden in ("RAW-CLOUD-PAYLOAD", "qa-secret", "projects/private", "Traceback"):
            assert forbidden not in text


@pytest.mark.parametrize("origins", ["https://one.example,https://two.example", " https://one.example, ,https://two.example, "])
def test_cors_origins_come_from_environment_with_empty_entries_removed(monkeypatch, origins, readiness_clients):
    import main
    monkeypatch.setenv("ALLOWED_ORIGINS", origins)
    importlib.reload(main)
    try:
        middleware = main.app.user_middleware[0]
        assert middleware.kwargs["allow_origins"] == ["https://one.example", "https://two.example"]
        for origin in ("https://one.example", "https://two.example"):
            response = TestClient(main.app).get("/api/health", headers={"Origin": origin})
            assert response.headers["access-control-allow-origin"] == origin
    finally:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        importlib.reload(main)


def test_cors_default_is_localhost_8501(monkeypatch, readiness_clients):
    import main
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    importlib.reload(main)
    assert main.app.user_middleware[0].kwargs["allow_origins"] == ["http://localhost:8501"]
    response = TestClient(main.app).get("/api/health", headers={"Origin": "http://localhost:8501"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:8501"


def test_cors_has_no_wildcards_and_does_not_echo_disallowed_origin(monkeypatch, readiness_clients):
    import main
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://allowed.example")
    importlib.reload(main)
    try:
        options = main.app.user_middleware[0].kwargs
        assert options["allow_methods"] == ["GET", "POST"]
        assert options["allow_headers"] == ["Content-Type"]
        assert all("*" not in options[key] for key in ("allow_origins", "allow_methods", "allow_headers"))
        client = TestClient(main.app)
        assert "access-control-allow-origin" not in client.get("/api/health", headers={"Origin": "https://evil.example"}).headers
        response = client.options("/api/analyze", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
    finally:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        importlib.reload(main)


@pytest.mark.parametrize("unavailable", [None, "gemini", "firestore", "pubsub", "bigquery"])
def test_health_probes_dependencies_and_returns_200_with_readiness_states(api_environment, readiness_clients, monkeypatch, unavailable):
    main = api_environment[0]
    probes = {
        "gemini": readiness_clients["gemini"].models.get,
        "firestore": readiness_clients["firestore"].collection.return_value.limit.return_value.get,
        "pubsub": readiness_clients["pubsub"].get_topic,
        "bigquery": readiness_clients["bigquery"].query,
    }
    if unavailable is not None:
        probes[unavailable].side_effect = GoogleAPIError("unavailable")
    original = asyncio.to_thread
    threaded_dependencies = []

    async def tracked_to_thread(function, *args, **kwargs):
        assert function is main.check_dependency
        threaded_dependencies.append(args[0])
        return await original(function, *args, **kwargs)

    monkeypatch.setattr(main.asyncio, "to_thread", tracked_to_thread)
    response = TestClient(main.app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "operational" if unavailable is None else "degraded",
        "dependencies": {
            name: "unavailable" if name == unavailable else "ready" for name in main.DEPENDENCIES
        },
        "region": "asia-southeast1",
    }
    assert sorted(threaded_dependencies) == sorted(main.DEPENDENCIES)
    for probe in probes.values():
        probe.assert_called_once()
    probes["gemini"].assert_called_once_with(
        model="gemini-2.5-flash", config={"http_options": {"timeout": 4500}}
    )
    readiness_clients["firestore"].collection.assert_called_once_with(main.database.COLLECTION_NAME)
    readiness_clients["firestore"].collection.return_value.limit.assert_called_once_with(1)
    probes["firestore"].assert_called_once_with(timeout=4.5, retry=None)
    probes["pubsub"].assert_called_once_with(
        request={"topic": "projects/qa/topics/alerts"}, timeout=4.5, retry=None
    )
    assert probes["bigquery"].call_args.kwargs["job_config"].dry_run is True
    assert probes["bigquery"].call_args.kwargs["timeout"] == 4.5
    readiness_clients["gemini"].models.generate_content.assert_not_called()
    readiness_clients["pubsub"].publish.assert_not_called()


def test_live_returns_200_without_cloud_calls(api_environment, readiness_clients, monkeypatch):
    main = api_environment[0]
    probe = Mock(side_effect=AssertionError("Liveness must not probe dependencies"))
    monkeypatch.setattr(main, "check_dependency", probe)
    response = TestClient(main.app).get("/api/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    probe.assert_not_called()
    for client in readiness_clients.values():
        assert client.mock_calls == []
    api_environment[1].assert_not_called()
    api_environment[2].assert_not_called()
    api_environment[3].assert_not_called()
    api_environment[4].collection.assert_not_called()


def test_pubsub_client_failure_keeps_analysis_successful_and_stored_false(api_environment, sample_png_bytes, monkeypatch):
    from services import alert_dispatcher

    monkeypatch.setattr(api_environment[0], "dispatch_heat_alert", alert_dispatcher.dispatch_heat_alert)
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", Mock(side_effect=GoogleAPIError("unreachable")))
    response = TestClient(api_environment[0].app, raise_server_exceptions=False).post("/api/analyze", files={"file": ("district.png", sample_png_bytes, "image/png")})
    assert response.status_code == 200
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["alert_dispatched"] is False


def test_pubsub_publish_failure_stores_false_without_raw_cloud_logging(api_environment, sample_png_bytes, monkeypatch, capsys, caplog):
    from services import alert_dispatcher

    secret = "RAW-CLOUD-PAYLOAD Bearer qa-secret projects/private/topics/private"
    publisher = Mock()
    publisher.publish.return_value.result.side_effect = GoogleAPIError(secret)
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", Mock(return_value=publisher))
    monkeypatch.setattr(api_environment[0], "dispatch_heat_alert", alert_dispatcher.dispatch_heat_alert)
    response = upload(api_environment, sample_png_bytes)
    assert response.status_code == 200
    stored = api_environment[4].collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["alert_dispatched"] is False
    captured = capsys.readouterr()
    for text in (response.text, captured.out, captured.err, caplog.text):
        assert "qa-secret" not in text
        assert "RAW-CLOUD-PAYLOAD" not in text


@pytest.mark.parametrize("content_type,payload,expected", [("text/plain", b"invalid", 415), ("image/png", b"x" * 10_000_001, 413)], ids=["wrong-content-type", "oversized"])
def test_unsafe_uploads_are_rejected_before_cloud_calls(api_environment, content_type, payload, expected):
    response = TestClient(api_environment[0].app).post("/api/analyze", files={"file": ("unsafe.txt", payload, content_type)})
    assert response.status_code == expected
    api_environment[1].assert_not_called()
    api_environment[2].assert_not_called()
    api_environment[3].assert_not_called()
    api_environment[4].collection.assert_not_called()


@pytest.mark.parametrize("size,expected", [(9_999_999, 200), (10_000_000, 200), (10_000_001, 413)])
def test_upload_limit_uses_decimal_ten_megabyte_boundary(api_environment, size, expected):
    assert api_environment[0].MAX_UPLOAD_BYTES == 10_000_000
    # Must be a real PNG: the signature check now runs before the size check.
    png_signature = b"\x89PNG\r\n\x1a\n"
    response = upload(api_environment, png_signature + b"x" * (size - len(png_signature)))
    assert response.status_code == expected
    if expected == 200:
        api_environment[1].assert_awaited_once()
        assert len(api_environment[1].await_args.kwargs["image_bytes"]) == size
    else:
        api_environment[1].assert_not_called()
        api_environment[2].assert_not_called()
        api_environment[3].assert_not_called()
        api_environment[4].collection.assert_not_called()


def test_analyze_requires_upload_or_complete_imagery_coordinates(api_environment):
    main, analyzer, climate, dispatch, firestore = api_environment
    response = TestClient(main.app).post("/api/analyze")
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}
    analyzer.assert_not_called()
    climate.assert_not_called()
    dispatch.assert_not_called()
    firestore.collection.assert_not_called()


@pytest.mark.parametrize("lat,lng", [(90, 180), (-90, -180)])
def test_imagery_cache_hit_accepts_inclusive_coordinate_boundaries(api_environment, monkeypatch, lat, lng):
    main = api_environment[0]
    cached = {"image_bytes": b"cached-image", "mime_type": "image/png"}
    lookup = Mock(return_value=cached)
    monkeypatch.setattr(main, "get_cached_satellite_imagery", lookup)
    response = TestClient(main.app).get("/api/imagery", params={"lat": lat, "lng": lng})
    assert response.status_code == 200
    assert response.content == cached["image_bytes"]
    assert response.headers["content-type"] == "image/png"
    lookup.assert_called_once_with(float(lat), float(lng))


@pytest.mark.parametrize("lat,lng", [(91, 0), (0, 181)])
def test_imagery_rejects_out_of_range_coordinates_before_cache_lookup(api_environment, monkeypatch, lat, lng):
    main = api_environment[0]
    lookup = Mock()
    monkeypatch.setattr(main, "get_cached_satellite_imagery", lookup)
    response = TestClient(main.app).get("/api/imagery", params={"lat": lat, "lng": lng})
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}
    lookup.assert_not_called()


def test_imagery_cache_miss_returns_opaque_502(api_environment, monkeypatch, caplog):
    main = api_environment[0]
    secret = "RAW-CLOUD-PAYLOAD projects/private/maps-key qa-secret"
    lookup = Mock(side_effect=main.MapsImageryError(secret))
    monkeypatch.setattr(main, "get_cached_satellite_imagery", lookup)
    response = TestClient(main.app, raise_server_exceptions=False).get(
        "/api/imagery", params={"lat": 1.3521, "lng": 103.8198}
    )
    assert response.status_code == 502
    assert set(response.json()) == {"code", "message"}
    for text in (response.text, caplog.text):
        for forbidden in ("RAW-CLOUD-PAYLOAD", "projects/private", "qa-secret"):
            assert forbidden not in text
    lookup.assert_called_once_with(1.3521, 103.8198)


def test_maps_request_budget_returns_generic_502(api_environment, monkeypatch, caplog):
    from tools.maps_imagery_service import MapsImageryRateLimitError

    main = api_environment[0]
    secret = "Maps imagery request allowance exhausted: qa-secret provider-detail"
    fetch = Mock(side_effect=MapsImageryRateLimitError(secret))
    monkeypatch.setattr(main, "fetch_satellite_imagery", fetch)
    response = TestClient(main.app, raise_server_exceptions=False).post(
        "/api/analyze", data={"imagery_lat": "1.3521", "imagery_lng": "103.8198"}
    )
    assert response.status_code == 502
    assert response.json() == {
        "code": "imagery_unavailable",
        "message": "Satellite imagery is unavailable.",
    }
    assert "qa-secret" not in response.text
    assert "provider-detail" not in caplog.text
    fetch.assert_called_once_with(1.3521, 103.8198)