from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data_samples"


@pytest.fixture
def coverage_dashboard(monkeypatch, sample_png_bytes, valid_report):
    image = BytesIO(sample_png_bytes)
    image.name = "coverage-district.png"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: image)
    post = Mock(return_value=Mock(status_code=200, json=lambda: valid_report))
    get = Mock(return_value=Mock(status_code=200, json=lambda: {"scans": []}))
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    original_glob = Path.glob
    monkeypatch.setattr(Path, "glob", lambda path, pattern: iter(()) if path == SAMPLES else original_glob(path, pattern))
    return AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=10), post, get


def click_control(app, label):
    app.run()
    assert not app.exception
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception
    return app


def select_upload_mode(app):
    app.run()
    assert not app.exception
    next(control for control in app.segmented_control if control.label == "Analysis source").set_value("Upload image").run()
    assert not app.exception
    return app


@pytest.mark.parametrize("status,message,element", [
    ("operational", "Backend operational", "success"),
    ("degraded", "Backend degraded", "warning"),
    ("unknown", "Backend readiness unavailable", "info"),
])
def test_health_check_renders_each_readiness_state_and_dependency(coverage_dashboard, status, message, element):
    app, post, get = coverage_dashboard
    get.return_value.json = lambda: {"status": status, "dependencies": {"firestore": "ready"}}
    click_control(app, "Check backend health")
    assert any(message in entry.value for entry in getattr(app, element))
    assert any("firestore: ready" in entry.value for entry in app.text)
    assert get.call_args.args[0].endswith("/api/health")
    assert get.call_args.kwargs["timeout"] == (5, 60)
    post.assert_not_called()


@pytest.mark.parametrize("failure", ["connection", "timeout", "http", "invalid-json"])
def test_health_check_failures_are_sanitized_without_analysis_calls(coverage_dashboard, failure, caplog):
    app, post, get = coverage_dashboard
    secret = "RAW-CLOUD-PAYLOAD projects/private Bearer qa-secret"
    if failure in {"connection", "timeout"}:
        error_type = requests.ConnectionError if failure == "connection" else requests.Timeout
        get.side_effect = error_type(secret)
    elif failure == "http":
        get.return_value = Mock(status_code=503, json=lambda: {"code": "UNAVAILABLE", "message": "Please retry."}, text=secret)
    else:
        get.return_value.json = Mock(side_effect=ValueError(secret))
    click_control(app, "Check backend health")
    assert app.error
    for entry in app.error:
        assert "qa-secret" not in entry.value
        assert "projects/private" not in entry.value
    assert "qa-secret" not in caplog.text
    post.assert_not_called()


@pytest.mark.parametrize("envelope", [[], {"code": 123, "message": "retry"}, None], ids=["list", "wrong-code-type", "invalid-json"])
def test_invalid_error_envelope_uses_generic_message(coverage_dashboard, envelope):
    app, post, _ = coverage_dashboard
    post.return_value = Mock(status_code=502, json=Mock(return_value=envelope))
    if envelope is None:
        post.return_value.json.side_effect = ValueError("private-payload")
    click_control(app, "Run HotSpot Analysis")
    assert any("Please try again shortly" in entry.value for entry in app.error)
    assert all("private-payload" not in entry.value for entry in app.error)


@pytest.mark.parametrize("filename,content,message", [
    ("large.png", None, "upload limit"),
    ("wrong.webp", b"\x89PNG\r\n\x1a\n", "Unsupported image type"),
    ("mismatch.png", b"not-a-png", "does not match"),
    ("corrupt.png", b"\x89PNG\r\n\x1a\n", "could not be opened"),
], ids=["oversized", "unsupported", "wrong-signature", "corrupt-image"])
def test_invalid_preview_blocks_analysis_before_http_request(
    coverage_dashboard, monkeypatch, filename, content, message,
):
    app, post, get = coverage_dashboard
    image = BytesIO(content if content is not None else b"x" * 10_000_001)
    image.name = filename
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: image)
    select_upload_mode(app)
    app.run()
    assert not app.exception
    assert any(message in entry.value for entry in app.error)
    assert not any(button.label == "Run HotSpot Analysis" for button in app.button)
    post.assert_not_called()
    get.assert_not_called()


def test_non_object_analysis_result_is_rejected_without_render_crash(coverage_dashboard):
    app, post, _ = coverage_dashboard
    post.return_value.json = lambda: []
    click_control(app, "Run HotSpot Analysis")
    assert app.error
    assert "analysis_result" not in app.session_state


def test_missing_image_renders_prompt_without_network(coverage_dashboard, monkeypatch):
    app, post, get = coverage_dashboard
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: None)
    select_upload_mode(app)
    assert not app.exception
    assert any("Select a preset or upload" in entry.value for entry in app.info)
    post.assert_not_called()
    get.assert_not_called()


@pytest.mark.parametrize("failure", [False, True], ids=["loaded", "unavailable"])
def test_selected_preset_loads_or_renders_safe_file_error(
    coverage_dashboard, sample_png_bytes, monkeypatch, failure,
):
    app, post, get = coverage_dashboard
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: None)
    preset = SAMPLES / "qa-coverage-preset.png"
    original_glob = Path.glob
    original_is_file = Path.is_file
    original_stat = Path.stat
    original_read = Path.read_bytes
    monkeypatch.setattr(Path, "glob", lambda path, pattern: iter([preset]) if path == SAMPLES else original_glob(path, pattern))
    monkeypatch.setattr(Path, "is_file", lambda path: True if path == preset else original_is_file(path))
    monkeypatch.setattr(Path, "stat", lambda path, **kwargs: SimpleNamespace(st_mtime_ns=int(failure)) if path == preset else original_stat(path, **kwargs))

    def read_preset(path):
        if path != preset:
            return original_read(path)
        if failure:
            raise OSError("private-file-path")
        return sample_png_bytes

    monkeypatch.setattr(Path, "read_bytes", read_preset)
    select_upload_mode(app)
    assert not app.exception
    next(control for control in app.selectbox if control.label == "Preset image").select(preset.name).run()
    assert not app.exception
    if failure:
        assert any("Preset image unavailable" in entry.value for entry in app.error)
        assert all("private-file-path" not in entry.value for entry in app.error)
        post.assert_not_called()
    else:
        next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
        assert not app.exception
        post.assert_called_once()
        assert post.call_args.kwargs["files"]["file"] == (preset.name, sample_png_bytes, "image/png")
    get.assert_not_called()


def test_preset_discovery_failure_leaves_custom_upload_available(coverage_dashboard, monkeypatch):
    app, post, get = coverage_dashboard
    original_glob = Path.glob
    # Return None so this really is the "no file selected" case; the shared fixture's
    # uploader yields a valid PNG, which previously made the assertion below vacuous.
    uploader = Mock(return_value=None)
    monkeypatch.setattr(st, "file_uploader", uploader)

    def broken_discovery(path, pattern):
        if path == SAMPLES:
            raise OSError("private-directory")
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", broken_discovery)
    select_upload_mode(app)
    assert not app.exception
    assert any("No preset images available" in entry.value for entry in app.info)
    uploader.assert_called_once_with("Upload urban aerial photo", type=["jpg", "jpeg", "png"])
    assert not any(button.label == "Run HotSpot Analysis" for button in app.button)
    post.assert_not_called()
    get.assert_not_called()


def test_unknown_risk_and_null_interventions_render_without_inventing_values(coverage_dashboard, valid_report):
    valid_report["risk_level"] = "UNKNOWN"
    valid_report["passive_cooling_plan"]["micro_canopy_interventions"] = [None, "Plant shade trees"]
    app = click_control(coverage_dashboard[0], "Run HotSpot Analysis")
    assert any(entry.value == "Risk level: -" for entry in app.caption)
    assert [control.label for control in app.checkbox] == ["Plant shade trees"]


def test_legacy_history_missing_dispatch_flag_renders_unknown_not_confirmation(coverage_dashboard, valid_report):
    app, post, get = coverage_dashboard
    valid_report.pop("alert_dispatched")
    get.return_value.json = lambda: {"scans": [valid_report]}
    click_control(app, "Refresh Recent Audits")
    assert any(entry.value == "Pub/Sub alert dispatched: -" for entry in app.text)
    assert not any("Published successfully" in entry.value for entry in app.error)
    post.assert_not_called()