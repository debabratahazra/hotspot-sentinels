"""Location discovery in the dashboard (STORY-049 to STORY-053).

Four input methods must land on the same coordinate pair without fighting each
other, so most of what matters here is their interaction.

The place typeahead is a custom component, which AppTest cannot drive, so these
tests stub it to return a chosen suggestion. The real widget is verified against
the deployed page; a green run here is not evidence that the component renders.
"""

import re
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import streamlit as st
import streamlit_searchbox
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "frontend/app.py")

GEOCODED = {"lat": 28.655, "lng": 77.1888, "formatted_address": "Karol Bagh, New Delhi, Delhi, India"}
REVERSE_GEOCODED = {"lat": 1.2897, "lng": 103.754, "formatted_address": "Singapore"}
SEARCHBOX_KEYS = ("place_search_sidebar", "place_search_map")
SUGGESTIONS = {"suggestions": [
    {"description": "Karol Bagh, New Delhi, Delhi, India", "place_id": "PLACE-1"},
    {"description": "Karol Bagh Metro Station, New Delhi, India", "place_id": "PLACE-2"},
]}


@pytest.fixture
def dashboard(monkeypatch, valid_report, sample_png_bytes):
    image = BytesIO(sample_png_bytes)
    image.name = "district.png"
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: image)
    post = Mock(return_value=Mock(status_code=200, json=lambda: valid_report))

    def routed_get(url, **kwargs):
        if "/api/places/suggest" in url:
            return Mock(status_code=200, json=lambda: SUGGESTIONS)
        if "/api/geocode/reverse" in url:
            return Mock(status_code=200, json=lambda: REVERSE_GEOCODED)
        if "/api/geocode" in url:
            return Mock(status_code=200, json=lambda: GEOCODED)
        return Mock(status_code=200, json=lambda: {"scans": [valid_report]})

    get = Mock(side_effect=routed_get)
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    return AppTest.from_file(APP, default_timeout=10), post, get


@pytest.fixture
def choose_suggestion(monkeypatch):
    """Pick a suggestion once, as the real component does before it resets."""
    def choose(place_id, description="Karol Bagh, New Delhi, Delhi, India"):
        remaining = [(description, place_id)]
        monkeypatch.setattr(streamlit_searchbox, "st_searchbox",
                            lambda *a, **k: remaining.pop() if remaining else None)
    return choose


@pytest.fixture
def suggestion_source(monkeypatch):
    """Capture the function the typeahead calls per keystroke, to exercise it directly."""
    captured = {}

    def stub(search_function, *args, **kwargs):
        captured["fn"] = search_function
        return None

    monkeypatch.setattr(streamlit_searchbox, "st_searchbox", stub)
    return captured


def coordinates(app):
    boxes = {box.label: box.value for box in app.text_input}
    return boxes["Latitude"], boxes["Longitude"]


def search(app, place_id="PLACE-1", *, choose):
    app.run()
    choose(place_id)
    app.run()
    assert not app.exception
    return app


def test_choosing_a_suggestion_sets_the_analysis_coordinates(dashboard, choose_suggestion):
    app = search(dashboard[0], choose=choose_suggestion)
    assert coordinates(app) == ("28.655000", "77.188800")


def test_the_resolved_place_is_shown_back_so_a_wrong_match_is_obvious(dashboard, choose_suggestion):
    app = search(dashboard[0], choose=choose_suggestion)
    assert any("Karol Bagh" in element.value for element in app.success)


def test_a_suggestion_is_resolved_by_place_id_not_by_its_text(dashboard, choose_suggestion):
    # Two places can share a name; the id is what makes the choice exact.
    app = search(dashboard[0], choose=choose_suggestion)
    geocode_calls = [call for call in dashboard[2].call_args_list
                     if "/api/geocode" in str(call)]
    assert geocode_calls, "choosing a suggestion must resolve it"
    assert geocode_calls[-1].kwargs["params"] == {"place_id": "PLACE-1"}
    assert not app.exception


def test_choosing_a_suggestion_switches_the_preset_to_custom(dashboard, choose_suggestion):
    # Otherwise the shortcut would still claim to describe the coordinates.
    app = search(dashboard[0], choose=choose_suggestion)
    assert next(box.value for box in app.selectbox if box.label == "Location shortcut") == "Custom coordinates"


def test_a_failed_resolution_leaves_coordinates_untouched(dashboard, monkeypatch, choose_suggestion):
    app = dashboard[0]
    app.run()
    before = coordinates(app)

    def not_found(url, **kwargs):
        if "/api/geocode" in url:
            return Mock(status_code=404, json=lambda: {"detail": "No place matched that search."})
        return Mock(status_code=200, json=lambda: {"scans": []})

    monkeypatch.setattr(requests, "get", Mock(side_effect=not_found))
    app = search(app, choose=choose_suggestion)
    assert coordinates(app) == before
    assert any(element.value for element in app.error)


def test_a_geocoding_outage_does_not_break_the_page(dashboard, monkeypatch, choose_suggestion):
    def failing(url, **kwargs):
        if "/api/geocode" in url:
            raise requests.ConnectionError("RAW-CLOUD-PAYLOAD AIzaSyLEAKED Bearer secret")
        return Mock(status_code=200, json=lambda: {"scans": []})

    monkeypatch.setattr(requests, "get", Mock(side_effect=failing))
    app = search(dashboard[0], choose=choose_suggestion)
    assert not app.exception
    rendered = " ".join(element.value for group in (app.error, app.warning, app.info) for element in group)
    assert "AIzaSy" not in rendered and "Bearer" not in rendered


def test_the_chosen_suggestions_own_wording_is_what_is_shown(dashboard, choose_suggestion):
    # Geocoding returns the official name, which for many places differs from
    # the one the operator clicked; showing it back reads as a mis-pick.
    app = dashboard[0]
    app.run()
    choose_suggestion("PLACE-9", description="Salt Lake City, Kolkata, West Bengal, India")
    app.run()
    assert not app.exception
    assert app.session_state["resolved_place"] == "Salt Lake City, Kolkata, West Bengal, India"
    assert coordinates(app) == ("28.655000", "77.188800"), "coordinates still come from the geocoder"


def test_both_search_boxes_are_reset_together_so_they_cannot_disagree(dashboard, choose_suggestion):
    # Two inputs showing different places while one coordinate is live would
    # leave the operator unsure which location is actually being analysed.
    app = search(dashboard[0], choose=choose_suggestion)
    source = Path(APP).read_text()
    assert "for searchbox in SEARCHBOX_KEYS" in source, (
        "applying a coordinate must clear every typeahead, not just the one used"
    )
    assert app.session_state.get("resolved_place") == GEOCODED["formatted_address"]
    assert not any(key in app.session_state for key in ("place_search_sidebar", "place_search_map"))


def test_both_search_boxes_seed_from_the_same_resolved_place(dashboard):
    # default_searchterm is what puts the active place into each box, so both
    # must read it from one piece of state rather than keeping their own.
    source = Path(APP).read_text()
    seeds = re.findall(r"default_searchterm=([^,\n]+)", source)
    assert seeds, "the typeahead must seed its text from the active place"
    assert all("resolved_place" in seed for seed in seeds)


def test_a_short_query_makes_no_suggestion_request(dashboard, suggestion_source):
    app = dashboard[0]
    app.run()
    # Autocomplete is billed per keystroke, so short prefixes must stay local.
    assert suggestion_source["fn"]("Ka") == []
    assert not any("/api/places/suggest" in str(call) for call in dashboard[2].call_args_list)


def test_a_long_enough_query_returns_label_and_place_id_pairs(dashboard, suggestion_source):
    app = dashboard[0]
    app.run()
    assert suggestion_source["fn"]("Karol Ba") == [
        ("Karol Bagh, New Delhi, Delhi, India",
         ("Karol Bagh, New Delhi, Delhi, India", "PLACE-1")),
        ("Karol Bagh Metro Station, New Delhi, India",
         ("Karol Bagh Metro Station, New Delhi, India", "PLACE-2")),
    ]


def test_a_suggestion_outage_returns_nothing_rather_than_interrupting_typing(
        dashboard, monkeypatch, suggestion_source):
    app = dashboard[0]
    app.run()
    monkeypatch.setattr(requests, "get", Mock(side_effect=requests.ConnectionError("AIzaSyLEAKED")))
    assert suggestion_source["fn"]("Karol Ba") == []
    assert not app.exception


def test_preset_shortcut_still_sets_coordinates(dashboard):
    app = dashboard[0]
    app.run()
    next(box for box in app.selectbox if box.label == "Location shortcut").set_value(
        "Singapore Botanic Gardens").run()
    assert not app.exception
    assert coordinates(app) == ("1.3521", "103.8198")


def test_a_preset_clears_search_text_left_over_from_an_earlier_place(dashboard):
    # The map moved but both boxes still read the previous search, so the screen
    # named one place while analysing another. The component keeps its displayed
    # text under its own key, so seed that rather than driving the stub.
    app = dashboard[0]
    app.run()
    for key in SEARCHBOX_KEYS:
        app.session_state[key] = {"result": None, "search": "Karol Bagh, New Delhi, Delhi, India"}

    next(box for box in app.selectbox if box.label == "Location shortcut").set_value(
        "Singapore Botanic Gardens").run()
    assert not app.exception
    assert app.session_state["resolved_place"] == "Singapore Botanic Gardens"
    # The component re-seeds its own key on render, so what matters is the text
    # it now displays, not whether the key was momentarily dropped.
    for key in SEARCHBOX_KEYS:
        assert app.session_state[key]["search"] == "Singapore Botanic Gardens", (
            f"{key} still names the previous place"
        )


def test_every_path_that_moves_the_coordinate_clears_the_searchboxes():
    # Three paths set a coordinate — preset, search and map click. A path that
    # forgets this leaves the boxes naming somewhere the map is no longer showing.
    source = Path(APP).read_text()
    assert source.count("reset_place_searchboxes()") >= 3, (
        "preset, pending-coordinate and the helper itself must all be present"
    )
    preset = source[source.index("def apply_location_preset"):]
    assert "reset_place_searchboxes()" in preset[:preset.index("\ndef ", 1)]


def test_search_result_survives_into_the_analysis_request(dashboard, choose_suggestion):
    app = search(dashboard[0], choose=choose_suggestion)
    next(button for button in app.button if button.label == "Run HotSpot Analysis").click().run()
    assert not app.exception
    sent = dashboard[1].call_args.kwargs.get("data") or {}
    # The app parses the text inputs to floats before sending.
    assert float(sent["imagery_lat"]) == pytest.approx(28.655)
    assert float(sent["imagery_lng"]) == pytest.approx(77.1888)


def test_a_map_click_is_applied_on_the_next_run(dashboard):
    # The picker cannot write the coordinate widgets itself, so it defers the
    # click and the next run applies it. This is that handover.
    app = dashboard[0]
    app.run()
    app.session_state["pending_coordinate"] = (1.2897, 103.754, "Chosen from the map")
    app.run()
    assert not app.exception
    assert coordinates(app) == ("1.289700", "103.754000")


def test_an_applied_map_click_is_not_replayed_on_later_runs(dashboard):
    app = dashboard[0]
    app.run()
    app.session_state["pending_coordinate"] = (1.2897, 103.754, "Chosen from the map")
    app.run()
    next(box for box in app.text_input if box.label == "Latitude").set_value("5.000000").run()
    # A stale pending click would stamp the map coordinate back over the edit.
    assert coordinates(app)[0] == "5.000000"


def test_a_map_click_is_named_rather_than_labelled_as_a_click():
    # "Chosen from the map" tells an operator nothing about where they clicked;
    # it survives only as the fallback when naming the point fails.
    source = Path(APP).read_text()
    picker = source[source.index("def render_location_picker"):]
    assignment = picker[picker.index("pending_coordinate"):][:260]
    assert "describe_point(" in assignment, "a map click must name the point it set"
    assert "MAP_CLICK_FALLBACK_LABEL" in source


def test_pending_coordinates_are_applied_before_the_widgets_exist():
    # The live failure this guards: the picker renders after the sidebar, so
    # writing imagery_latitude from inside it raised
    # StreamlitWidgetAlreadyInstantiatedError on every map click.
    source = Path(APP).read_text()
    # Match the module-level call, not the def, or moving the call would pass.
    call = re.search(r"^apply_pending_coordinate\(\)$", source, re.MULTILINE)
    assert call, "the app must call apply_pending_coordinate() at module level"
    assert call.start() < source.index('key="imagery_latitude"'), (
        "apply_pending_coordinate() must run before the coordinate widgets"
    )
