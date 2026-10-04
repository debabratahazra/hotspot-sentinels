import copy
import importlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from requests.exceptions import RequestException

from services import database


def test_complete_reports_save_generated_ids_and_unchanged_analysis_timestamps(fake_firestore, valid_report):
    original = copy.deepcopy(valid_report)
    assert database.save_hotspot_report(valid_report) == "generated-scan-id"
    fake_firestore.collection.assert_called_once_with("hotspot_scans")
    document = fake_firestore.collection.return_value.document
    document.assert_called_once_with()
    stored = document.return_value.set.call_args.args[0]
    assert stored == original
    assert stored is not valid_report
    assert valid_report == original
    fake_firestore.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [SimpleNamespace(to_dict=lambda: stored)]
    assert database.get_recent_reports() == [original]


@pytest.mark.parametrize("limit,expected", [(0, 1), (-5, 1), (10000, 100), (100, 100), (10, 10)])
def test_history_is_newest_first_with_limits_clamped(fake_firestore, limit, expected):
    assert database.get_recent_reports(limit) == []
    collection = fake_firestore.collection.return_value
    collection.order_by.assert_called_once_with("timestamp", direction=database.firestore.Query.DESCENDING)
    collection.order_by.return_value.limit.assert_called_once_with(expected)


@pytest.mark.parametrize("value", ["ten", 1.5, True, None])
def test_history_rejects_non_integer_limits_without_client_calls(fake_firestore, value):
    with pytest.raises(TypeError, match="must be an integer"):
        database.get_recent_reports(value)
    fake_firestore.collection.assert_not_called()


def test_returned_timestamps_are_recursive_utc_iso8601_and_json_safe(fake_firestore):
    naive = datetime(2026, 10, 2, 12)
    offset = datetime(2026, 10, 2, 20, tzinfo=timezone(timedelta(hours=8)))
    report = {"timestamp": offset, "created_at": naive, "nested": {"dates": (offset, naive)}, "plain": 4}
    query = fake_firestore.collection.return_value.order_by.return_value.limit.return_value
    query.stream.return_value = [SimpleNamespace(to_dict=lambda: report)]
    result = database.get_recent_reports()[0]
    assert result["timestamp"] == result["created_at"] == "2026-10-02T12:00:00+00:00"
    assert result["nested"]["dates"] == [result["timestamp"], result["timestamp"]]
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize("operation", ["client", "write", "read"])
@pytest.mark.parametrize("error_type", [GoogleAPIError, GoogleAuthError, RequestException])
def test_firestore_client_write_and_read_failures_raise_safe_database_error(monkeypatch, fake_firestore, valid_report, caplog, operation, error_type):
    payload = "RAW-CLOUD-PAYLOAD token=qa-secret projects/private/databases/private"
    error = error_type(payload)
    if operation == "client":
        monkeypatch.setattr(database, "_client", None)
        monkeypatch.setattr(database.firestore, "Client", Mock(side_effect=error))
        function = database.get_db
        importlib.reload(database)
        function = database.get_db
    elif operation == "write":
        fake_firestore.collection.return_value.document.return_value.set.side_effect = error
        function = lambda: database.save_hotspot_report(valid_report)
    else:
        fake_firestore.collection.return_value.order_by.return_value.limit.return_value.stream.side_effect = error
        function = database.get_recent_reports
    with pytest.raises(database.DatabaseError) as caught:
        function()
    assert caught.value.__suppress_context__
    for text in (str(caught.value), caplog.text):
        assert "qa-secret" not in text
        assert "RAW-CLOUD-PAYLOAD" not in text
        assert "projects/private" not in text


def test_reports_missing_timestamps_receive_server_generated_created_at(fake_firestore):
    report = {"zone_id": "missing-time"}
    before = datetime.now(timezone.utc)
    database.save_hotspot_report(report)
    stored = fake_firestore.collection.return_value.document.return_value.set.call_args.args[0]
    assert stored["created_at"] is database.firestore.SERVER_TIMESTAMP
    assert before <= datetime.fromisoformat(stored["timestamp"]) <= datetime.now(timezone.utc)
    assert report == {"zone_id": "missing-time"}


def test_firestore_client_is_lazy_environment_configured_and_cached(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "qa-project")
    constructor = Mock()
    monkeypatch.setattr(database.firestore, "Client", constructor)
    importlib.reload(database)
    try:
        constructor.assert_not_called()
        assert database.get_db() is constructor.return_value
        assert database.get_db() is constructor.return_value
        constructor.assert_called_once()
        assert constructor.call_args.kwargs["project"] == "qa-project"
    finally:
        monkeypatch.setattr(database, "_client", None)