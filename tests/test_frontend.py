import ast
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest


@pytest.fixture
def dashboard(monkeypatch, valid_report, sample_png_bytes):
    image = BytesIO(sample_png_bytes)
    image.name = "district.png"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: image)
    post = Mock(return_value=Mock(status_code=200, json=lambda: valid_report))
    get = Mock(return_value=Mock(status_code=200, json=lambda: {"scans": [valid_report]}))
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/app.py"), default_timeout=10), post, get


def click(app, label):
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


def test_no_deleted_schema_field_is_referenced_in_frontend():
    tree = ast.parse(Path("frontend/app.py").read_text())
    deleted = {"requires_emergency_alert", "surface_temp_estimate_c"}
    assert not [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in deleted]


@pytest.mark.parametrize("view", ["Run HotSpot Analysis", "Refresh Recent Audits"])
@pytest.mark.parametrize("band,dispatched,confirmed", [("CRITICAL", True, True), ("CRITICAL", False, False), ("HIGH", True, False)])
def test_critical_alert_confirmation_uses_risk_and_dispatch_as_separate_facts(dashboard, valid_report, view, band, dispatched, confirmed):
    valid_report.update(risk_level=band, alert_dispatched=dispatched)
    app = click(dashboard[0], view)
    confirmations = [element.value for element in app.error if "alert dispatched" in element.value]
    assert bool(confirmations) is confirmed
    warnings = [element.value for element in app.warning if "dispatch not confirmed" in element.value]
    assert bool(warnings) is (band == "CRITICAL" and not dispatched)


@pytest.mark.parametrize("view", ["Run HotSpot Analysis", "Refresh Recent Audits"])
@pytest.mark.parametrize("missing", [False, True])
def test_no_metric_or_history_value_renders_none(dashboard, valid_report, view, missing):
    if missing:
        valid_report.clear()
        valid_report.update(risk_level="CRITICAL", alert_dispatched=False)
    app = click(dashboard[0], view)
    values = [element.value for group in (app.metric, app.markdown, app.info, app.success) for element in group if isinstance(element.value, str)]
    values.extend(element.label for element in app.expander)
    assert all("None" not in value for value in values)
    if view == "Run HotSpot Analysis":
        assert len(app.metric) == 7
        assert app.metric[2].label == "Projected Cooling Drop"
        assert app.metric[2].value == ("-" if missing else "6.8 \u00b0C")
        if missing:
            assert all(metric.value == "-" for metric in app.metric)


def test_empty_scans_render_without_exception(dashboard):
    dashboard[2].return_value.json = lambda: {"scans": []}
    app = click(dashboard[0], "Refresh Recent Audits")
    assert any("No prior scans" in element.value for element in app.info)


@pytest.mark.parametrize("view", ["Run HotSpot Analysis", "Refresh Recent Audits"])
def test_api_unreachable_renders_gracefully(dashboard, view):
    request = dashboard[1] if view == "Run HotSpot Analysis" else dashboard[2]
    request.side_effect = requests.ConnectionError("offline")
    app = click(dashboard[0], view)
    assert app.error or app.warning


@pytest.mark.parametrize("view", ["Run HotSpot Analysis", "Refresh Recent Audits"])
@pytest.mark.parametrize("failure", ["exception", "timeout", "unexpected", "response"])
def test_dashboard_errors_do_not_disclose_raw_cloud_payloads(dashboard, view, failure, caplog):
    secret = "RAW-CLOUD-PAYLOAD Bearer qa-secret projects/private/buckets/private"
    request = dashboard[1] if view == "Run HotSpot Analysis" else dashboard[2]
    if failure != "response":
        error_type = {"exception": requests.ConnectionError, "timeout": requests.Timeout, "unexpected": RuntimeError}[failure]
        request.side_effect = error_type(secret)
    else:
        request.return_value.status_code = 503
        request.return_value.text = secret
    app = click(dashboard[0], view)
    assert app.error
    assert all("qa-secret" not in element.value and "RAW-CLOUD-PAYLOAD" not in element.value for group in (app.error, app.warning) for element in group)
    for forbidden in ("qa-secret", "RAW-CLOUD-PAYLOAD", "projects/private", "Traceback"):
        assert forbidden not in caplog.text
    records = [record for record in caplog.records if record.name == "__main__"]
    assert records
    assert all(not record.exc_info for record in records)


@pytest.mark.parametrize("view,endpoint", [("Run HotSpot Analysis", "/api/analyze"), ("Refresh Recent Audits", "/api/scans?limit=5")])
@pytest.mark.parametrize("base_url", [None, "https://qa.example/"])
def test_dashboard_requests_use_environment_url_and_explicit_timeouts(dashboard, monkeypatch, view, endpoint, base_url):
    if base_url is None:
        monkeypatch.delenv("API_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("API_BASE_URL", base_url)
    click(dashboard[0], view)
    request = dashboard[1] if view == "Run HotSpot Analysis" else dashboard[2]
    request.assert_called_once()
    assert request.call_args.args[0] == f"{(base_url or 'http://localhost:8080').rstrip('/')}{endpoint}"
    assert request.call_args.kwargs["timeout"] == (5, 60)


def test_dark_theme_is_applied_from_script_level_config():
    import tomllib

    config = tomllib.loads(Path("frontend/.streamlit/config.toml").read_text())
    assert config["theme"]["base"] == "dark"
    assert config["theme"]["primaryColor"] == "#e2aa41"


def test_location_mode_is_default_and_city_preset_submits_coordinates_without_file(dashboard):
    app = dashboard[0].run()
    assert not app.exception
    assert app.segmented_control[0].value == "Satellite location"
    next(control for control in app.selectbox if control.label == "Location shortcut").select("Bangkok").run()
    assert not app.exception
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {"imagery_lat": 13.7563, "imagery_lng": 100.5018}
    assert dashboard[1].call_args.kwargs["files"] is None


def test_arbitrary_location_submits_entered_coordinates_without_file(dashboard):
    app = dashboard[0].run()
    assert not app.exception
    next(control for control in app.text_input if control.label == "Latitude").set_value("-12.3456").run()
    next(control for control in app.text_input if control.label == "Longitude").set_value("145.6789").run()
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {"imagery_lat": -12.3456, "imagery_lng": 145.6789}
    assert dashboard[1].call_args.kwargs["files"] is None


@pytest.mark.parametrize("label,value", [
    ("Latitude", "-90"), ("Latitude", "90"),
    ("Longitude", "-180"), ("Longitude", "180"),
])
def test_location_coordinate_inclusive_boundaries_are_accepted(dashboard, label, value):
    app = dashboard[0].run()
    assert not app.exception
    next(control for control in app.text_input if control.label == label).set_value(value).run()
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    data = dashboard[1].call_args.kwargs["data"]
    assert data["imagery_lat"] == (-90.0 if label == "Latitude" and value == "-90" else 90.0 if label == "Latitude" else 1.3521)
    assert data["imagery_lng"] == (-180.0 if label == "Longitude" and value == "-180" else 180.0 if label == "Longitude" else 103.8198)
    assert dashboard[1].call_args.kwargs["files"] is None


@pytest.mark.parametrize("label,value", [
    ("Latitude", "-90.0001"), ("Latitude", "90.0001"),
    ("Longitude", "-180.0001"), ("Longitude", "180.0001"),
])
def test_out_of_range_committed_location_blocks_submission(dashboard, label, value):
    app = dashboard[0].run()
    assert not app.exception
    next(control for control in app.text_input if control.label == label).set_value(value).run()
    assert any("Coordinates must be finite" in element.value for element in app.error)
    assert not any(button.label == "Run HotSpot Analysis" for button in app.button)
    dashboard[1].assert_not_called()


def test_upload_mode_submits_file_without_imagery_coordinates(dashboard, sample_png_bytes):
    app = select_upload_mode(dashboard[0])
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {}
    assert dashboard[1].call_args.kwargs["files"] == {
        "file": ("district.png", sample_png_bytes, "image/png"),
    }


@pytest.mark.parametrize("source,element,message,other_element", [
    ("google_maps", "success", "SATELLITE IMAGERY · Retrieved by the backend for this location", "info"),
    ("caller", "info", "CALLER IMAGE · Analyst-provided imagery", "success"),
])
def test_image_source_provenance_renders_distinctly(dashboard, valid_report, source, element, message, other_element):
    valid_report["image_source"] = source
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert any(message in entry.value for entry in getattr(app, element))
    assert not any(message in entry.value for entry in getattr(app, other_element))


@pytest.mark.parametrize("status,code,message", [
    (422, "INVALID_COORDINATES", "Coordinates are outside the supported range."),
    (502, "imagery_unavailable", "Satellite imagery is unavailable."),
])
def test_location_api_error_envelopes_render_safely(dashboard, status, code, message, caplog):
    secret_payload = "RAW-CLOUD-PAYLOAD https://maps.googleapis.com/maps/api/staticmap?key=AIzaSyFAKEKEY"
    dashboard[1].return_value = Mock(
        status_code=status,
        json=lambda: {"code": code, "message": message},
        text=secret_payload,
    )
    app = click(dashboard[0], "Run HotSpot Analysis")
    rendered_errors = [element.value for element in app.error]
    assert any(f"HTTP {status}" in value and f"[{code}]" in value and message in value for value in rendered_errors)
    assert not app.exception
    assert all(secret_payload not in value and "AIza" not in value and "Traceback" not in value for value in rendered_errors)
    assert "RAW-CLOUD-PAYLOAD" not in caplog.text
    assert "AIza" not in caplog.text


def test_maps_api_key_and_static_map_url_are_not_browser_visible(dashboard, valid_report):
    valid_report["image_source"] = "google_maps"
    app = click(dashboard[0], "Run HotSpot Analysis")
    element_types = (
        "title", "header", "subheader", "caption", "text", "markdown", "info", "success",
        "warning", "error", "button", "selectbox", "text_input", "segmented_control", "metric",
    )
    browser_text = "\n".join(
        f"{getattr(element, 'label', '')} {getattr(element, 'value', '')} {getattr(element, 'options', '')}"
        for kind in element_types for element in app.get(kind)
    )
    browser_text += repr(dashboard[1].call_args)
    browser_text += Path("frontend/app.py").read_text()
    for forbidden in ("AIza", "maps.googleapis.com", "maps.google.com/maps/api"):
        assert forbidden not in browser_text


def test_city_image_and_default_off_what_if_temperature_controls_are_present(dashboard, monkeypatch):
    uploader = Mock(wraps=st.file_uploader)
    monkeypatch.setattr(st, "file_uploader", uploader)
    app = dashboard[0].run()
    assert not app.exception
    assert app.segmented_control[0].value == "Satellite location"
    assert app.selectbox[0].options == ["Singapore", "Bangkok", "Delhi", "Custom coordinates"]
    assert app.selectbox[0].label == "Location shortcut"
    uploader.assert_not_called()
    assert len(app.toggle) == 1
    assert app.toggle[0].label == "Use what-if temperature"
    assert app.toggle[0].value is False
    assert not app.slider
    assert not app.number_input
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {"imagery_lat": 1.3521, "imagery_lng": 103.8198}
    assert dashboard[1].call_args.kwargs["files"] is None


def test_enabling_what_if_temperature_exposes_bounded_input_with_default_and_step(dashboard):
    app = dashboard[0].run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert len(app.number_input) == 1
    control = app.number_input[0]
    assert control.label == "What-if ambient temperature (\u00b0C)"
    assert control.value == 35.0
    assert control.min == -50.0
    assert control.max == 60.0
    assert control.step == 0.5
    dashboard[1].assert_not_called()


@pytest.mark.parametrize("temperature", [-50.0, 35.5, 60.0])
def test_enabled_what_if_temperature_sends_chosen_value_and_inclusive_boundaries(dashboard, sample_png_bytes, temperature):
    app = dashboard[0].run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception
    app.number_input[0].set_value(temperature).run()
    assert not app.exception
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {
        "ambient_temp_c": temperature, "imagery_lat": 1.3521, "imagery_lng": 103.8198,
    }
    assert dashboard[1].call_args.kwargs["files"] is None


def test_disabling_what_if_temperature_omits_previously_chosen_value(dashboard):
    app = dashboard[0].run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception
    app.number_input[0].set_value(42.5).run()
    assert not app.exception
    app.toggle[0].set_value(False).run()
    assert not app.exception
    assert not app.number_input
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    dashboard[1].assert_called_once()
    assert dashboard[1].call_args.kwargs["data"] == {"imagery_lat": 1.3521, "imagery_lng": 103.8198}
    assert dashboard[1].call_args.kwargs["files"] is None


@pytest.mark.parametrize("temperature", [-50.5, 60.5, float("nan"), float("inf"), float("-inf")])
def test_invalid_what_if_temperature_is_refused_before_http_request(dashboard, monkeypatch, temperature):
    app = dashboard[0].run()
    assert not app.exception
    monkeypatch.setattr(st, "number_input", lambda *args, **kwargs: temperature)
    app.toggle[0].set_value(True).run()
    assert not app.exception
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    assert app.error
    assert "analysis_result" not in app.session_state
    dashboard[1].assert_not_called()
    dashboard[2].assert_not_called()


@pytest.mark.parametrize("source,treatment,message", [
    ("bigquery", "success", "MEASURED TELEMETRY \u00b7 BigQuery / NOAA GSOD"),
    ("fallback", "info", "Live climate telemetry unavailable. This report uses the backend's fallback temperature."),
    ("caller", "warning", "WHAT-IF \u00b7 Analyst-supplied temperature. Not measured telemetry."),
])
def test_climate_source_renders_distinct_measured_fallback_and_what_if_treatments(dashboard, valid_report, source, treatment, message):
    valid_report["climate_source"] = source
    app = click(dashboard[0], "Run HotSpot Analysis")
    provenance_messages = {
        "MEASURED TELEMETRY \u00b7 BigQuery / NOAA GSOD",
        "Live climate telemetry unavailable. This report uses the backend's fallback temperature.",
        "WHAT-IF \u00b7 Analyst-supplied temperature. Not measured telemetry.",
    }
    rendered = [(kind, element.value) for kind in ("success", "info", "warning") for element in getattr(app, kind) if element.value in provenance_messages]
    assert rendered == [(treatment, message)]


@pytest.mark.parametrize("score,band,color", [
    (3.9, "LOW", "green"), (4.0, "MODERATE", "green"),
    (5.9, "MODERATE", "green"), (6.0, "HIGH", "orange"),
    (7.9, "HIGH", "orange"), (8.0, "CRITICAL", "red"),
])
def test_badge_colour_matches_every_hvi_band_exactly(dashboard, valid_report, monkeypatch, score, band, color):
    valid_report.update(hvi_score=score, risk_level=band)
    badge = Mock(wraps=st.badge)
    monkeypatch.setattr(st, "badge", badge)
    click(dashboard[0], "Run HotSpot Analysis")
    badge.assert_called_once_with(band, color=color)


def test_image_and_score_are_rendered_in_adjacent_columns(dashboard):
    app = select_upload_mode(dashboard[0])
    app = click(app, "Run HotSpot Analysis")
    columns = [node for node in app.get("column") if node.get("image") or node.get("metric")]
    assert len(columns) >= 2
    image_columns = [node for node in columns if node.get("image")]
    assert len(image_columns) == 1
    assert any(metric.label == "HVI (1-10)" for node in columns if not node.get("image") for metric in node.get("metric"))


@pytest.mark.parametrize("source,label", [("bigquery", "BigQuery / NOAA GSOD"), ("fallback", "Offline fallback")])
def test_temperature_is_shown_in_celsius_with_provenance(dashboard, valid_report, source, label):
    valid_report["climate_source"] = source
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert next(metric for metric in app.metric if metric.label == "Ambient Temp").value == "38.5 \u00b0C"
    assert any(f"Temperature source: {label}" == caption.value for caption in app.caption)


def test_surface_breakdown_is_charted_with_fixed_material_colours(dashboard, valid_report):
    app = click(dashboard[0], "Run HotSpot Analysis")
    charts = app.get("vega_lite_chart")
    assert len(charts) == 1
    spec = json.loads(charts[0].proto.spec)
    assert spec["encoding"]["color"]["scale"] == {
        "domain": ["Asphalt", "Dark Roofs", "Concrete", "Green Canopy"],
        "range": ["#555555", "#181818", "#c9cdd1", "#43b879"],
    }
    assert spec["encoding"]["x"]["scale"]["domain"] == [0, 100]
    assert [metric.value for metric in app.metric[3:]] == ["55%", "30%", "10%", "5%"]


def test_corridor_orientation_is_shown(dashboard):
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert any(text.value == "NE-SW" for text in app.text)


def test_coating_area_and_projected_drop_use_metric_units(dashboard):
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert any(text.value == "4200 m\u00b2" for text in app.text)
    assert any(text.value == "6.8 \u00b0C" for text in app.text)


def test_micro_canopy_interventions_are_listed(dashboard, valid_report):
    app = click(dashboard[0], "Run HotSpot Analysis")
    assert [checkbox.label for checkbox in app.checkbox] == valid_report["passive_cooling_plan"]["micro_canopy_interventions"]


@pytest.mark.parametrize("attempted,dispatched,expected", [
    (False, False, "Publication not attempted"),
    (True, False, "Publication attempted and failed"),
    (True, True, "Published successfully"),
])
def test_alert_banner_distinguishes_not_attempted_failed_and_published(dashboard, valid_report, attempted, dispatched, expected):
    valid_report.update(alert_attempted=attempted, alert_dispatched=dispatched)
    app = click(dashboard[0], "Run HotSpot Analysis")
    messages = [element.value for group in (app.error, app.warning) for element in group]
    assert any(expected in message for message in messages)


def test_spinner_is_active_during_analysis_request(dashboard, monkeypatch):
    from contextlib import contextmanager

    active = []
    original = st.spinner

    @contextmanager
    def spinner(*args, **kwargs):
        active.append(args[0])
        try:
            with original(*args, **kwargs):
                yield
        finally:
            active.pop()

    monkeypatch.setattr(st, "spinner", spinner)
    response = dashboard[1].return_value

    def post(*args, **kwargs):
        assert active
        assert "Analyzing" in active[-1]
        return response

    dashboard[1].side_effect = post
    click(dashboard[0], "Run HotSpot Analysis")
    dashboard[1].assert_called_once()
    assert active == []


@pytest.mark.parametrize("image_format,mime", [("JPEG", "image/jpeg"), ("PNG", "image/png")])
def test_dashboard_multipart_preserves_real_jpeg_and_png_types(dashboard, monkeypatch, image_format, mime):
    from PIL import Image

    image = BytesIO()
    Image.new("RGB", (8, 8), (40, 120, 50)).save(image, format=image_format)
    image.name = "district." + image_format.lower()
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: image)
    app = select_upload_mode(dashboard[0])
    click(app, "Run HotSpot Analysis")
    assert dashboard[1].call_args.kwargs["files"] == {"file": (image.name, image.getvalue(), mime)}


def test_criterion_1_attribution_required_coordinate_image_keeps_watermark_uncropped(dashboard, valid_report, monkeypatch):
    from PIL import Image, ImageDraw

    source_image = Image.new("RGB", (180, 72), "white")
    ImageDraw.Draw(source_image).text((120, 56), "Google Maps", fill="black")
    encoded_image = BytesIO()
    source_image.save(encoded_image, format="PNG")
    imagery_bytes = encoded_image.getvalue()
    valid_report.update(image_source="google_maps", attribution_required=True)
    dashboard[2].return_value = Mock(status_code=200, content=imagery_bytes)

    rendered_images = []
    original_image = st.image

    def capture_image(image, *args, **kwargs):
        rendered_images.append((image, args, kwargs))
        return original_image(image, *args, **kwargs)

    monkeypatch.setattr(st, "image", capture_image)
    app = click(dashboard[0], "Run HotSpot Analysis")

    assert not app.exception
    assert rendered_images[0][0] == imagery_bytes
    assert rendered_images[0][2]["width"] == "stretch"
    displayed_image = Image.open(BytesIO(rendered_images[0][0]))
    assert displayed_image.size == source_image.size
    assert displayed_image.crop((120, 56, 180, 72)).getbbox()
    assert any(caption.value == "Imagery from Google Maps" for caption in app.caption)


def test_criterion_2_dashboard_uses_api_imagery_without_maps_url_or_api_key(dashboard, monkeypatch, valid_report, sample_png_bytes):
    api_base_url = "https://qa.example/"
    api_key = "test-google-maps-api-key"
    monkeypatch.setenv("API_BASE_URL", api_base_url)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", api_key)
    valid_report.update(image_source="google_maps", attribution_required=True)
    dashboard[2].return_value = Mock(status_code=200, content=sample_png_bytes)

    app = click(dashboard[0], "Run HotSpot Analysis")

    assert not app.exception
    dashboard[2].assert_called_once_with(
        f"{api_base_url.rstrip('/')}/api/imagery",
        params={"lat": 1.3521, "lng": 103.8198},
        timeout=(5, 60),
    )
    outbound_requests = repr(dashboard[1].call_args_list + dashboard[2].call_args_list)
    assert "maps.googleapis.com" not in outbound_requests
    assert api_key not in outbound_requests
    assert app.image


def test_criterion_3_missing_attribution_image_shows_error_without_claiming_attribution(dashboard, valid_report):
    valid_report.update(image_source="google_maps", attribution_required=True)
    dashboard[2].return_value = Mock(status_code=502, content=b"")

    app = click(dashboard[0], "Run HotSpot Analysis")

    assert not app.exception
    assert any(
        "Required Google Maps attribution image is unavailable" in error.value
        and "not presented as attribution-compliant" in error.value
        for error in app.error
    )
    assert not any(caption.value == "Imagery from Google Maps" for caption in app.caption)
    assert not app.image