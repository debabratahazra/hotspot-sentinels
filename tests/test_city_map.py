"""City-wide heat map (STORY-047).

Exercised through the real dashboard script with the history response stubbed,
so these assert what a viewer actually gets rather than what a helper returns.
"""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "frontend/app.py")


@pytest.fixture
def dashboard(monkeypatch, valid_report, sample_png_bytes):
    image = BytesIO(sample_png_bytes)
    image.name = "district.png"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: image)
    post = Mock(return_value=Mock(status_code=200, json=lambda: valid_report))
    get = Mock(return_value=Mock(status_code=200, json=lambda: {"scans": [valid_report]}))
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    return AppTest.from_file(APP, default_timeout=10), post, get


def click(app, label):
    app.run()
    assert not app.exception
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception
    return app


def scans_response(dashboard, scans):
    dashboard[2].return_value.json = lambda: {"scans": scans}
    return click(dashboard[0], "Refresh Recent Audits")


def located(**overrides):
    scan = {
        "zone_id": "z1", "zone_name": "Port Terminal",
        "coordinates": {"lat": 1.2897, "lng": 103.754},
        "hvi_score": 8.1, "risk_level": "CRITICAL",
        "ambient_temp_c": 31.0, "alert_dispatched": True, "image_source": "google_maps",
    }
    scan.update(overrides)
    return scan


def rgba(hex_colour):
    """Streamlit converts hex to an RGBA array before handing it to deck.gl."""
    value = hex_colour.lstrip("#")
    return [int(value[index:index + 2], 16) for index in (0, 2, 4)] + [255]


def map_points(app):
    charts = app.get("deck_gl_json_chart")
    assert charts, "the city map should render as a map chart"
    spec = json.loads(charts[0].proto.json)
    for layer in spec.get("layers", []):
        if layer.get("data"):
            return layer["data"]
    return []


def test_located_scans_render_as_map_points(dashboard):
    app = scans_response(dashboard, [located(), located(zone_id="z2", risk_level="LOW", hvi_score=1.5)])
    points = map_points(app)
    assert len(points) == 2


@pytest.mark.parametrize("band,colour", [
    ("CRITICAL", "#ff4d4f"), ("HIGH", "#ff9f43"), ("MODERATE", "#ffd166"), ("LOW", "#2dd4a7"),
])
def test_marker_colour_follows_the_risk_band(dashboard, band, colour):
    app = scans_response(dashboard, [located(risk_level=band)])
    assert map_points(app)[0]["colour"] == rgba(colour)


def test_unknown_risk_band_still_plots_with_a_neutral_colour(dashboard):
    app = scans_response(dashboard, [located(risk_level="SOMETHING-NEW")])
    point = map_points(app)[0]
    assert point["colour"] == rgba("#8b9aad"), "an unrecognised band must not drop the marker"


def test_marker_size_grows_with_hvi(dashboard):
    low = map_points(scans_response(dashboard, [located(hvi_score=1.5)]))[0]["size"]
    high = map_points(scans_response(dashboard, [located(hvi_score=9.0)]))[0]["size"]
    assert high > low


@pytest.mark.parametrize("coordinates", [
    None, {}, {"lat": 1.0}, {"lng": 103.0},
    {"lat": None, "lng": 103.0}, {"lat": "1.0", "lng": "103.0"},
    {"lat": True, "lng": False},
])
def test_scan_without_usable_coordinates_is_skipped_not_crashed(dashboard, coordinates):
    # An uploaded image has no coordinates; it must not take the map down.
    app = scans_response(dashboard, [located(coordinates=coordinates), located(zone_id="z2")])
    assert len(map_points(app)) == 1
    assert not app.exception


def test_map_shows_an_explicit_message_when_nothing_is_located(dashboard):
    app = scans_response(dashboard, [located(coordinates=None)])
    assert any("Analyse a coordinate" in element.value for element in app.info)
    assert not app.exception


def test_legend_explains_the_colour_coding(dashboard):
    app = scans_response(dashboard, [located()])
    captions = [element.value for element in app.caption]
    assert any("CRITICAL" in caption and "risk band" in caption for caption in captions)


def map_zoom(app):
    spec = json.loads(app.get("deck_gl_json_chart")[0].proto.json)
    return spec["initialViewState"]["zoom"]


def test_nearby_zones_are_framed_at_city_scale_not_the_whole_globe(dashboard):
    # st.map without an explicit zoom frames the world for a few nearby points,
    # which renders the markers as unreadable specks.
    app = scans_response(dashboard, [
        located(coordinates={"lat": 1.2897, "lng": 103.7540}),
        located(zone_id="z2", coordinates={"lat": 1.3521, "lng": 103.8198}),
    ])
    assert map_zoom(app) >= 9


def test_far_apart_zones_zoom_out_enough_to_show_both(dashboard):
    app = scans_response(dashboard, [
        located(coordinates={"lat": 1.3521, "lng": 103.8198}),
        located(zone_id="z2", coordinates={"lat": 28.6450, "lng": 77.2200}),
    ])
    assert map_zoom(app) <= 4


def test_model_invented_coordinates_from_uploads_are_not_plotted(dashboard):
    # An uploaded image has no real location, but the model still returns a
    # plausible-looking coordinate; one such scan put a Singapore zone in Los
    # Angeles and dragged the whole map out to a world view.
    app = scans_response(dashboard, [
        located(),
        located(zone_id="upload", image_source="caller",
                coordinates={"lat": 34.0522, "lng": -118.2437}),
    ])
    points = map_points(app)
    assert len(points) == 1
    assert points[0]["lat"] == pytest.approx(1.2897)
