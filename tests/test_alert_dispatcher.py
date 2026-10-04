import importlib
import os
from concurrent.futures import TimeoutError
from copy import deepcopy
from unittest.mock import Mock

import pytest
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud.pubsub_v1.publisher.exceptions import MessageTooLargeError
from grpc import RpcError
from requests.exceptions import RequestException

from services import alert_dispatcher


@pytest.fixture(autouse=True)
def reset_publisher_cache(monkeypatch):
    monkeypatch.setattr(alert_dispatcher, "_client", None)


@pytest.mark.parametrize("operation", ["client", "topic", "publish"])
@pytest.mark.parametrize("error_type", [GoogleAPIError, GoogleAuthError, RequestException, RpcError, TimeoutError, MessageTooLargeError])
def test_dispatch_failures_return_empty_id_and_type_only_logs(monkeypatch, valid_report, caplog, capsys, operation, error_type):
    secret = "RAW-CLOUD-PAYLOAD Bearer qa-secret projects/private/topics/private"
    publisher = Mock()
    constructor = Mock(return_value=publisher)
    failure = error_type(secret)
    if operation == "client":
        constructor.side_effect = failure
    elif operation == "topic":
        publisher.topic_path.side_effect = failure
    else:
        publisher.publish.return_value.result.side_effect = failure
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == ""
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err
    records = [record for record in caplog.records if record.name == alert_dispatcher.__name__]
    assert len(records) == 1
    assert records[0].getMessage() == f"Heat alert dispatch failed: {error_type.__name__}"
    assert not records[0].exc_info
    for forbidden in ("RAW-CLOUD-PAYLOAD", "qa-secret", "projects/private", "Traceback"):
        assert forbidden not in caplog.text


def test_dispatcher_import_is_lazy_and_never_shells_out(monkeypatch):
    def reject_shell(*args, **kwargs):
        raise AssertionError("Import must not shell out")

    monkeypatch.setattr(os, "popen", reject_shell)
    constructor = Mock()
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    importlib.reload(alert_dispatcher)
    constructor.assert_not_called()


def test_successful_dispatch_lazily_caches_publisher(monkeypatch, valid_report):
    publisher = Mock()
    publisher.publish.return_value.result.return_value = "published-message-id"
    constructor = Mock(return_value=publisher)
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == "published-message-id"
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == "published-message-id"
    constructor.assert_called_once()
    assert publisher.publish.call_count == 2


@pytest.fixture
def assert_invalid_alert(monkeypatch, caplog, valid_report):
    report = deepcopy(valid_report)
    report["private_payload"] = "RAW-PAYLOAD Bearer qa-secret projects/private"
    constructor = Mock()
    get_client = Mock()
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    monkeypatch.setattr(alert_dispatcher, "_get_client", get_client)

    def check(payload=report, exception_type="ValueError"):
        assert alert_dispatcher.dispatch_heat_alert(payload) == ""
        get_client.assert_not_called()
        constructor.assert_not_called()
        records = [record for record in caplog.records if record.name == alert_dispatcher.__name__]
        assert len(records) == 1
        assert records[0].getMessage() == f"Heat alert dispatch failed: {exception_type}"
        assert records[0].args == (exception_type,)
        assert not records[0].exc_info
        for forbidden in ("RAW-PAYLOAD", "qa-secret", "projects/private", "qa-zone", "QA District", "Plant shade corridors", "Traceback"):
            assert forbidden not in caplog.text

    return report, check


@pytest.mark.parametrize("field", ["zone_id", "coordinates", "ambient_temp_c", "hvi_score", "timestamp", "passive_cooling_plan"])
def test_missing_required_alert_field_is_rejected_before_client_creation(assert_invalid_alert, field):
    report, check = assert_invalid_alert
    del report[field]
    check()


@pytest.mark.parametrize("field", ["lat", "lng"])
def test_missing_required_coordinate_is_rejected_before_client_creation(assert_invalid_alert, field):
    report, check = assert_invalid_alert
    del report["coordinates"][field]
    check()


def test_missing_intervention_list_is_rejected_before_client_creation(assert_invalid_alert):
    report, check = assert_invalid_alert
    del report["passive_cooling_plan"]["micro_canopy_interventions"]
    check()


@pytest.mark.parametrize("field,value", [("lat", -90.1), ("lat", 90.1), ("lng", -180.1), ("lng", 180.1)])
def test_out_of_range_coordinates_are_rejected_before_client_creation(assert_invalid_alert, field, value):
    report, check = assert_invalid_alert
    report["coordinates"][field] = value
    check()


def test_naive_scan_timestamp_is_rejected_before_client_creation(assert_invalid_alert):
    report, check = assert_invalid_alert
    report["timestamp"] = "2026-10-02T12:00:00"
    check()


def test_malformed_scan_timestamp_is_rejected_before_client_creation(assert_invalid_alert):
    report, check = assert_invalid_alert
    report["timestamp"] = "RAW-PAYLOAD invalid timestamp"
    check()


def test_utc_timestamp_normalization_overflow_is_rejected_before_client_creation(assert_invalid_alert):
    report, check = assert_invalid_alert
    report["timestamp"] = "0001-01-01T00:00:00+14:00"
    check(exception_type="OverflowError")


@pytest.mark.parametrize("count", [0, 6], ids=["empty", "above_five"])
def test_invalid_intervention_count_is_rejected_before_client_creation(assert_invalid_alert, count):
    report, check = assert_invalid_alert
    report["passive_cooling_plan"]["micro_canopy_interventions"] = ["Plant shade corridors"] * count
    check()


@pytest.mark.parametrize("field,limit", [("zone_id", 128), ("zone_name", 256), ("region", 64), ("timestamp", 64), ("intervention", 512)])
@pytest.mark.parametrize("multibyte", [False, True], ids=["ascii", "utf8_byte_count"])
def test_alert_text_byte_limit_is_enforced_before_client_creation(assert_invalid_alert, monkeypatch, field, limit, multibyte):
    report, check = assert_invalid_alert
    value = "\u00e9" * (limit // 2 + 1) if multibyte else "x" * (limit + 1)
    assert len(value.encode("utf-8")) > limit
    if multibyte:
        assert len(value) <= limit
    if field == "region":
        monkeypatch.setattr(alert_dispatcher, "REGION", value)
    elif field == "intervention":
        report["passive_cooling_plan"]["micro_canopy_interventions"] = [value]
    else:
        report[field] = value
    check()


@pytest.mark.parametrize("field,value", [("zone_id", 123), ("zone_id", "   "), ("coordinates", []), ("passive_cooling_plan", []), ("ambient_temp_c", "38.5"), ("ambient_temp_c", True), ("hvi_score", "8.0")])
def test_wrong_type_or_blank_alert_field_is_rejected_before_client_creation(assert_invalid_alert, field, value):
    report, check = assert_invalid_alert
    report[field] = value
    check()


@pytest.mark.parametrize("value", ["Plant shade corridors", [123], ["   "]], ids=["not_list", "non_string_action", "blank_action"])
def test_invalid_intervention_type_is_rejected_before_client_creation(assert_invalid_alert, value):
    report, check = assert_invalid_alert
    report["passive_cooling_plan"]["micro_canopy_interventions"] = value
    check()


def test_non_dictionary_alert_payload_is_rejected_before_client_creation(assert_invalid_alert):
    report, check = assert_invalid_alert
    check(payload=[report])


@pytest.mark.parametrize("risk_level", [None, "LOW", "MODERATE", "HIGH"])
def test_analyzer_noncritical_risk_skips_client_even_with_critical_hvi(monkeypatch, valid_report, caplog, risk_level):
    valid_report["risk_level"] = risk_level
    constructor = Mock()
    get_client = Mock()
    monkeypatch.setattr(alert_dispatcher.pubsub_v1, "PublisherClient", constructor)
    monkeypatch.setattr(alert_dispatcher, "_get_client", get_client)
    assert alert_dispatcher.dispatch_heat_alert(valid_report) == ""
    get_client.assert_not_called()
    constructor.assert_not_called()
    assert not [record for record in caplog.records if record.name == alert_dispatcher.__name__]