import ast
import importlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.api_core.exceptions import GoogleAPIError
from google.api_core.exceptions import RetryError
from google.auth.exceptions import GoogleAuthError
from requests.exceptions import RequestException

from tools import climate_service


@pytest.fixture
def telemetry(monkeypatch):
    client = Mock()
    client.query.return_value.result.return_value = [
        SimpleNamespace(station_id="486980", observation_date=date(2024, 12, 31), max=104, temp=86)
    ]
    monkeypatch.setattr(climate_service, "_get_client", lambda: client)
    return client


def test_latest_valid_gsod_row_has_complete_bigquery_reading(telemetry):
    reading = climate_service.get_latest_temperature()
    assert reading == {
        "station_id": "486980", "observation_date": "2024-12-31",
        "max_temp_c": 40.0, "avg_temp_c": 30.0, "source": "bigquery",
    }
    query = telemetry.query.call_args.args[0]
    assert "ORDER BY observation_date DESC" in query
    assert "LIMIT 1" in query
    parameters = telemetry.query.call_args.kwargs["job_config"].query_parameters
    assert next(parameter.value for parameter in parameters if parameter.name == "table_year") == "2024"
    json.dumps(reading)


@pytest.mark.parametrize("field,value", [("max", 9999.9), ("temp", 9999.9), ("max", None), ("temp", None), ("max", float("nan")), ("temp", float("inf"))])
def test_maximum_and_average_convert_to_celsius_and_exclude_sentinels(telemetry, field, value):
    invalid = SimpleNamespace(station_id="486980", observation_date=date(2024, 12, 31), max=104, temp=86)
    setattr(invalid, field, value)
    valid = SimpleNamespace(station_id="486980", observation_date=date(2024, 12, 30), max=95, temp=77)
    telemetry.query.return_value.result.return_value = [invalid, valid]
    reading = climate_service.get_latest_temperature()
    assert reading["max_temp_c"] == 35.0
    assert reading["avg_temp_c"] == 25.0
    assert reading["observation_date"] == "2024-12-30"


def test_station_input_cannot_alter_sql_meaning(telemetry):
    malicious = "486980' OR TRUE; DROP TABLE scans; --"
    climate_service.get_latest_temperature(malicious)
    query = telemetry.query.call_args.args[0]
    assert "@station_id" in query
    assert malicious not in query
    assert "DROP TABLE" not in query
    parameters = telemetry.query.call_args.kwargs["job_config"].query_parameters
    assert next(parameter.value for parameter in parameters if parameter.name == "station_id") == malicious


def test_telemetry_clients_are_lazy_environment_configured_without_shellout(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "qa-project")
    monkeypatch.delenv("BIGQUERY_LOCATION", raising=False)
    monkeypatch.setenv("NOAA_GSOD_YEAR", "2024")
    constructor = Mock()
    monkeypatch.setattr(climate_service.bigquery, "Client", constructor)
    importlib.reload(climate_service)
    try:
        constructor.assert_not_called()
        assert climate_service._get_client() is constructor.return_value
        assert climate_service._get_client() is constructor.return_value
        constructor.assert_called_once()
        assert constructor.call_args.kwargs["project"] == "qa-project"
        assert constructor.call_args.kwargs["location"] == "US"
        source = Path("backend/tools/climate_service.py").read_text()
        assert "os.popen" not in source
        assert "gcloud" not in source
    finally:
        monkeypatch.setattr(climate_service, "_client", None)


def test_station_id_is_bound_as_scalar_query_parameter(telemetry):
    climate_service.get_latest_temperature("untrusted' OR 1=1 --")
    parameters = telemetry.query.call_args.kwargs["job_config"].query_parameters
    station = next(parameter for parameter in parameters if parameter.name == "station_id")
    assert isinstance(station, climate_service.bigquery.ScalarQueryParameter)
    assert station.type_ == "STRING"
    assert station.value == "untrusted' OR 1=1 --"
    assert station.value not in telemetry.query.call_args.args[0]


@pytest.mark.parametrize("field", ["max", "temp"])
def test_9999_9_sentinel_is_filtered_in_sql_and_in_code(telemetry, field):
    row = SimpleNamespace(station_id="486980", observation_date=date(2024, 12, 31), max=104, temp=86)
    setattr(row, field, 9999.9)
    telemetry.query.return_value.result.return_value = [row]
    reading = climate_service.get_latest_temperature()
    assert reading["source"] == "fallback"
    assert 35 <= reading["max_temp_c"] <= 41
    query = telemetry.query.call_args.args[0]
    assert "max != 9999.9" in query
    assert "temp != 9999.9" in query


@pytest.mark.parametrize("failure", [None, GoogleAPIError, GoogleAuthError, RequestException])
def test_fallback_reading_is_labelled_and_logs_no_raw_payload(telemetry, caplog, failure):
    secret = "token=qa-secret projects/private/topics/private RAW-CLOUD-PAYLOAD"
    if failure:
        telemetry.query.side_effect = failure(secret)
    else:
        telemetry.query.return_value.result.return_value = []
    reading = climate_service.get_latest_temperature("requested-station")
    assert reading == {
        "station_id": "requested-station", "observation_date": None,
        "max_temp_c": 38.5, "avg_temp_c": 32.5, "source": "fallback",
    }
    assert secret not in caplog.text
    assert "qa-secret" not in caplog.text
    assert "fallback" in caplog.text


def test_no_blanket_exception_hides_programming_errors(telemetry):
    tree = ast.parse(Path("backend/tools/climate_service.py").read_text())
    assert not any(isinstance(node, ast.ExceptHandler) and (node.type is None or isinstance(node.type, ast.Name) and node.type.id == "Exception") for node in ast.walk(tree))
    telemetry.query.side_effect = TypeError("programming defect")
    with pytest.raises(TypeError, match="programming defect"):
        climate_service.get_latest_temperature()


@pytest.fixture
def assert_invalid_temperature(telemetry):
    def check(field, value, valid_row_follows):
        station_id = "requested-station"
        invalid = SimpleNamespace(station_id=station_id, observation_date=date(2024, 12, 31), max=104, temp=86)
        setattr(invalid, field, value)
        rows = [invalid]
        if valid_row_follows:
            rows.append(SimpleNamespace(station_id=station_id, observation_date=date(2024, 12, 30), max=95, temp=77))
        telemetry.query.return_value.result.return_value = rows
        reading = climate_service.get_latest_temperature(station_id)
        assert reading == {
            "station_id": station_id,
            "observation_date": "2024-12-30" if valid_row_follows else None,
            "max_temp_c": 35.0 if valid_row_follows else 38.5,
            "avg_temp_c": 25.0 if valid_row_follows else 32.5,
            "source": "bigquery" if valid_row_follows else "fallback",
        }
        assert telemetry.query.call_args.kwargs["timeout"] == 5.0
        assert telemetry.query.call_args.kwargs["retry"] is None
        assert telemetry.query.call_args.kwargs["job_retry"] is None
        assert telemetry.query.return_value.result.call_args.kwargs == {
            "timeout": 10.0, "retry": None, "job_retry": None,
        }

    return check


@pytest.mark.parametrize("field", ["max", "temp"])
@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_null_temperature_row_falls_back_or_continues(assert_invalid_temperature, field, valid_row_follows):
    assert_invalid_temperature(field, None, valid_row_follows)


@pytest.mark.parametrize("field", ["max", "temp"])
@pytest.mark.parametrize("value", [9999.9, "9999.9"], ids=["numeric", "numeric_string"])
@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_noaa_sentinel_row_falls_back_or_continues(assert_invalid_temperature, field, value, valid_row_follows):
    assert_invalid_temperature(field, value, valid_row_follows)


@pytest.mark.parametrize("field", ["max", "temp"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "1e10000"], ids=["nan", "positive_infinity", "negative_infinity", "string_overflow_to_infinity"])
@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_nonfinite_temperature_row_falls_back_or_continues(assert_invalid_temperature, field, value, valid_row_follows):
    assert_invalid_temperature(field, value, valid_row_follows)


@pytest.mark.parametrize("field", ["max", "temp"])
@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_uncastable_temperature_row_falls_back_or_continues(assert_invalid_temperature, field, valid_row_follows):
    assert_invalid_temperature(field, "not-a-temperature", valid_row_follows)


@pytest.mark.parametrize("field", ["max", "temp"])
@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_float_conversion_overflow_row_falls_back_or_continues(assert_invalid_temperature, field, valid_row_follows):
    assert_invalid_temperature(field, 10 ** 400, valid_row_follows)


@pytest.mark.parametrize("valid_row_follows", [False, True], ids=["fallback", "skip_to_measured"])
def test_missing_observation_date_row_falls_back_or_continues(assert_invalid_temperature, valid_row_follows):
    assert_invalid_temperature("observation_date", None, valid_row_follows)


def test_missing_project_oserror_is_wrapped_and_returns_exact_fallback(monkeypatch):
    monkeypatch.setattr(climate_service, "_client", None)
    monkeypatch.setattr(climate_service, "PROJECT_ID", None)
    constructor = Mock(side_effect=OSError("missing project RAW-CLOUD-PAYLOAD"))
    monkeypatch.setattr(climate_service.bigquery, "Client", constructor)
    with pytest.raises(climate_service._ClimateClientError, match="BigQuery client configuration is unavailable"):
        climate_service._get_client()
    assert climate_service.get_latest_temperature("requested-station") == {
        "station_id": "requested-station", "observation_date": None,
        "max_temp_c": 38.5, "avg_temp_c": 32.5, "source": "fallback",
    }
    assert constructor.call_count == 2
    constructor.assert_called_with(project=None, location=climate_service.BIGQUERY_LOCATION)


@pytest.mark.parametrize("operation", ["client", "submission", "retrieval", "iteration"])
@pytest.mark.parametrize("failure", ["timeout", "retry_exhaustion"])
def test_timeout_or_retry_exhaustion_returns_exact_fallback(monkeypatch, telemetry, operation, failure, caplog):
    secret = "RAW-CLOUD-PAYLOAD Bearer qa-secret projects/private"
    error = TimeoutError(secret) if failure == "timeout" else RetryError(secret, GoogleAPIError(secret))
    if operation == "client":
        monkeypatch.setattr(climate_service, "_get_client", Mock(side_effect=error))
    elif operation == "submission":
        telemetry.query.side_effect = error
    elif operation == "retrieval":
        telemetry.query.return_value.result.side_effect = error
    else:
        def failing_rows():
            raise error
            yield

        telemetry.query.return_value.result.return_value = failing_rows()
    assert climate_service.get_latest_temperature("requested-station") == {
        "station_id": "requested-station", "observation_date": None,
        "max_temp_c": 38.5, "avg_temp_c": 32.5, "source": "fallback",
    }
    assert secret not in caplog.text
    assert "qa-secret" not in caplog.text


@pytest.mark.parametrize("error_type", [TypeError, KeyError])
def test_temperature_conversion_programming_errors_propagate(telemetry, error_type):
    value = Mock()
    value.__float__ = Mock(side_effect=error_type("programming defect"))
    telemetry.query.return_value.result.return_value = [
        SimpleNamespace(station_id="486980", observation_date=date(2024, 12, 31), max=value, temp=86)
    ]
    with pytest.raises(error_type, match="programming defect"):
        climate_service.get_latest_temperature()