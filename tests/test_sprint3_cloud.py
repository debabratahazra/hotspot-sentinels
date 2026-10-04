import ast
import asyncio
import copy
import inspect
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud.pubsub_v1.publisher.exceptions import MessageTooLargeError
from google.cloud.storage.exceptions import DataCorruption
from grpc import RpcError
from requests.exceptions import RequestException

from services import alert_dispatcher, database, vision_analyzer
from tools import climate_service, seed_samples

DATABASE_GET_CLIENT = database._get_client


def test_missing_project_climate_lookup_returns_labelled_fallback(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setattr(climate_service, "PROJECT_ID", None)
    monkeypatch.setattr(climate_service, "_client", None)
    constructor = Mock(side_effect=EnvironmentError("Project was not determined"))
    monkeypatch.setattr(climate_service.bigquery, "Client", constructor)
    reading = climate_service.get_latest_temperature()
    assert reading["source"] == "fallback"
    assert 35 <= reading["max_temp_c"] <= 41
    constructor.assert_called_once_with(project=None, location=climate_service.BIGQUERY_LOCATION)


@pytest.mark.parametrize("endpoint", ["/api/analyze", "/api/scans"])
def test_missing_project_firestore_raises_database_error_and_api_returns_503(
    api_environment, sample_png_bytes, monkeypatch, endpoint
):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setattr(database, "PROJECT_ID", None)
    monkeypatch.setattr(database, "_client", None)
    monkeypatch.setattr(database, "DatabaseError", api_environment[0].DatabaseError)
    monkeypatch.setattr(database, "_get_client", DATABASE_GET_CLIENT)
    constructor = Mock(side_effect=EnvironmentError("Project was not determined"))
    monkeypatch.setattr(database.firestore, "Client", constructor)
    with pytest.raises(database.DatabaseError):
        database.get_db()
    client = TestClient(api_environment[0].app, raise_server_exceptions=False)
    response = client.get(endpoint) if endpoint.endswith("scans") else client.post(
        endpoint, files={"file": ("zone.png", sample_png_bytes, "image/png")}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert "Project was not determined" not in response.text
    assert constructor.call_args.kwargs["project"] is None


def test_missing_project_seeder_warns_and_retains_generated_local_files(monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("GCS_BUCKET_NAME", "qa-bucket")
    monkeypatch.setattr(seed_samples, "DATA_DIR", tmp_path / "samples")
    monkeypatch.setattr(seed_samples, "_client", None)
    constructor = Mock(side_effect=EnvironmentError("Project was not determined"))
    monkeypatch.setattr(seed_samples.storage, "Client", constructor)
    paths = seed_samples.generate_samples()
    original = {path: path.read_bytes() for path in paths}
    assert seed_samples.upload_samples(paths) == []
    assert {path: path.read_bytes() for path in paths} == original
    assert "storage client unavailable" in caplog.text
    assert "Project was not determined" not in caplog.text
    assert constructor.call_args.kwargs["project"] is None


@pytest.mark.parametrize("module,sdk", [(climate_service, "bigquery"), (database, "firestore"), (seed_samples, "storage")])
@pytest.mark.parametrize("error_type", [TypeError, KeyError])
def test_typeerror_and_keyerror_still_propagate_from_client_construction(monkeypatch, module, sdk, error_type):
    monkeypatch.setattr(module, "_client", None)
    monkeypatch.setattr(getattr(module, sdk), "Client", Mock(side_effect=error_type("programming defect")))
    with pytest.raises(error_type, match="programming defect"):
        module._get_client()


@pytest.mark.parametrize("error_type", [TypeError, KeyError])
@pytest.mark.parametrize("operation", ["database_write", "database_read", "storage_bucket", "storage_upload"])
def test_typeerror_and_keyerror_still_propagate_from_database_and_seeder_operations(
    monkeypatch, tmp_path, valid_report, error_type, operation
):
    client = Mock()
    failure = error_type("programming defect")
    if operation.startswith("database"):
        monkeypatch.setattr(database, "_get_client", lambda: client)
        if operation == "database_write":
            client.collection.return_value.document.return_value.set.side_effect = failure
            invoke = lambda: database.save_hotspot_report(valid_report)
        else:
            client.collection.return_value.order_by.return_value.limit.return_value.stream.side_effect = failure
            invoke = database.get_recent_reports
    else:
        monkeypatch.setenv("GCS_BUCKET_NAME", "qa-bucket")
        monkeypatch.setattr(seed_samples, "_get_client", lambda: client)
        if operation == "storage_bucket":
            client.bucket.side_effect = failure
        else:
            client.bucket.return_value.blob.return_value.upload_from_filename.side_effect = failure
        invoke = lambda: seed_samples.upload_samples([tmp_path / "qa.jpg"])
    with pytest.raises(error_type, match="programming defect"):
        invoke()


def test_exception_boundary_matrix_proves_sdk_failure_inheritance():
    bases = (GoogleAPIError, GoogleAuthError, RequestException)
    assert EnvironmentError is OSError
    for error_type in (DataCorruption, RpcError, TimeoutError, MessageTooLargeError, OSError):
        assert not issubclass(error_type, bases)
    assert issubclass(DataCorruption, seed_samples.CLOUD_ERRORS)
    handlers = [node for node in ast.walk(ast.parse(inspect.getsource(alert_dispatcher.dispatch_heat_alert)))
                if isinstance(node, ast.ExceptHandler) and "RpcError" in ast.unparse(node.type)]
    assert len(handlers) == 1
    covered = eval(compile(ast.Expression(handlers[0].type), "<exception-proof>", "eval"), vars(alert_dispatcher))
    assert issubclass(RpcError, covered)
    assert issubclass(TimeoutError, covered)
    assert issubclass(MessageTooLargeError, covered)
    for error_type in (TypeError, KeyError):
        assert not issubclass(error_type, (*bases, OSError, DataCorruption, RpcError, TimeoutError, MessageTooLargeError))


@pytest.mark.parametrize("stage", ["client", "submit", "result"])
@pytest.mark.parametrize("error_type", [GoogleAPIError, GoogleAuthError, RequestException, TimeoutError])
def test_expected_climate_cloud_failures_return_complete_labelled_fallback(monkeypatch, stage, error_type, caplog):
    secret = "RAW-CLOUD-PAYLOAD projects/private Bearer qa-secret"
    client = Mock()
    constructor = Mock(return_value=client)
    monkeypatch.setattr(climate_service, "_client", None)
    monkeypatch.setattr(climate_service.bigquery, "Client", constructor)
    failure = error_type(secret)
    if stage == "client":
        constructor.side_effect = failure
    elif stage == "submit":
        client.query.side_effect = failure
    else:
        client.query.return_value.result.side_effect = failure
    reading = climate_service.get_latest_temperature("qa-station")
    assert reading == {"station_id": "qa-station", "observation_date": None,
                       "max_temp_c": 38.5, "avg_temp_c": 32.5, "source": "fallback"}
    assert "qa-secret" not in caplog.text
    assert "RAW-CLOUD-PAYLOAD" not in caplog.text


@pytest.mark.parametrize("error_type", [TypeError, KeyError])
def test_local_programming_errors_are_not_hidden_by_climate_fallback(monkeypatch, error_type):
    client = Mock()
    client.query.side_effect = error_type("programming defect")
    monkeypatch.setattr(climate_service, "_get_client", lambda: client)
    with pytest.raises(error_type, match="programming defect"):
        climate_service.get_latest_temperature()


def test_climate_submission_and_result_timeouts_are_bounded_with_retries_disabled(monkeypatch):
    client = Mock()
    client.query.return_value.result.return_value = []
    monkeypatch.setattr(climate_service, "_get_client", lambda: client)
    climate_service.get_latest_temperature()
    assert client.query.call_args.kwargs["timeout"] == 5.0
    assert client.query.call_args.kwargs["retry"] is None
    assert client.query.call_args.kwargs["job_retry"] is None
    client.query.return_value.result.assert_called_once_with(timeout=10.0, retry=None, job_retry=None)


@pytest.mark.parametrize("rows", [[], [SimpleNamespace(max=9999.9, temp=86)], [SimpleNamespace(max=104, temp=9999.9)]])
def test_empty_or_sentinel_only_climate_results_have_plausible_maximum_and_average_gap(monkeypatch, rows):
    client = Mock()
    client.query.return_value.result.return_value = rows
    monkeypatch.setattr(climate_service, "_get_client", lambda: client)
    reading = climate_service.get_latest_temperature()
    assert reading["source"] == "fallback"
    assert 35 <= reading["max_temp_c"] <= 41
    assert 5 <= reading["max_temp_c"] - reading["avg_temp_c"] <= 7


def test_hvi_rubric_uses_fixed_weights_calibration_and_zero_temperature(monkeypatch, valid_report, sample_png_bytes):
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(text=json.dumps(valid_report))
    monkeypatch.setattr(vision_analyzer, "get_client", lambda: client)
    reports = [asyncio.run(vision_analyzer.analyze_urban_hotspot(sample_png_bytes, 35.0)) for _ in range(2)]
    assert reports[0]["hvi_score"] == reports[1]["hvi_score"]
    for call in client.models.generate_content.call_args_list:
        config = call.kwargs["config"]
        assert config.temperature == 0.0
        assert config.system_instruction == vision_analyzer.SYSTEM_INSTRUCTION
        for component in ("0.45 * absorption", "0.25 * canopy_deficit", "0.10 * shade_deficit",
                          "0.10 * built_density", "0.10 * ambient_heat", "nearest 0.1",
                          "Round only the final score", "industrial_hotspot.jpg strictly above"):
            assert component in config.system_instruction


def test_industrial_asphalt_ranks_above_green_park_at_equal_ambient_in_mocked_rubric(monkeypatch, valid_report):
    surfaces = {b"industrial": (55, 30, 10, 5), b"park": (5, 0, 10, 85)}
    client = Mock()

    def scored_response(**kwargs):
        image = kwargs["contents"][0].inline_data.data
        asphalt, roof, concrete, canopy = surfaces[image]
        payload = copy.deepcopy(valid_report)
        payload["surface_breakdown"] = dict(zip(payload["surface_breakdown"], surfaces[image]))
        payload["hvi_score"] = round(1 + 9 * (
            0.45 * (asphalt + roof + 0.5 * concrete) / 100 +
            0.25 * (1 - canopy / 100) + 0.10 * 0.5 + 0.10 * roof / 100 + 0.10 * 0.75
        ), 1)
        return SimpleNamespace(text=json.dumps(payload))

    client.models.generate_content.side_effect = scored_response
    monkeypatch.setattr(vision_analyzer, "get_client", lambda: client)
    industrial = asyncio.run(vision_analyzer.analyze_urban_hotspot(b"industrial", 35.0))
    park = asyncio.run(vision_analyzer.analyze_urban_hotspot(b"park", 35.0))
    assert industrial["ambient_temp_c"] == park["ambient_temp_c"] == 35.0
    assert industrial["hvi_score"] > park["hvi_score"]