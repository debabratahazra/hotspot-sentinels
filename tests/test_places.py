"""Place autocomplete (STORY-051).

Same security property as geocoding: GOOGLE_MAPS_API_KEY is a backend concern,
so it must never reach a caller, a log line, or an error body. Autocomplete runs
on every keystroke, so the cost and failure behaviour matter as much as the data.
"""

import importlib
import logging
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

places = importlib.import_module("tools.places_service")

SECRET = "AIzaSy-this-is-the-secret-key-value"

OK_PAYLOAD = {
    "suggestions": [
        {"placePrediction": {"text": {"text": "Karol Bagh, New Delhi, Delhi, India"},
                             "placeId": "ChIJ0y5AX5wCDTkRRtmdTCl0IZQ"}},
        {"placePrediction": {"text": {"text": "Karol Bagh Metro Station, New Delhi, India"},
                             "placeId": "ChIJUerjap4CDTkRbZabc"}},
    ]
}


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    places._cache.clear()
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", SECRET)
    yield
    places._cache.clear()


def respond(monkeypatch, *, status_code=200, payload=None, error=None):
    def fake_post(url, json=None, headers=None, timeout=None):
        if error is not None:
            raise error
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        return response
    monkeypatch.setattr(places.requests, "post", fake_post)
    return fake_post


def client(monkeypatch, **kwargs):
    respond(monkeypatch, **kwargs)
    main = importlib.import_module("main")
    return TestClient(main.app)


def test_a_partial_name_returns_suggestions(monkeypatch):
    respond(monkeypatch, payload=OK_PAYLOAD)
    suggestions = places.suggest_places("Karol Ba")
    assert [item["description"] for item in suggestions][0].startswith("Karol Bagh")
    assert suggestions[0]["place_id"] == "ChIJ0y5AX5wCDTkRRtmdTCl0IZQ"


def test_a_query_shorter_than_the_minimum_costs_nothing(monkeypatch):
    called = []
    monkeypatch.setattr(places.requests, "post",
                        lambda *a, **k: called.append(1) or Mock(status_code=200))
    assert places.suggest_places("Ka") == []
    assert not called, "a 2-character query must not reach the provider"


def test_repeat_keystrokes_are_served_from_cache(monkeypatch):
    calls = []

    def counting_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        response = Mock(status_code=200)
        response.json.return_value = OK_PAYLOAD
        return response

    monkeypatch.setattr(places.requests, "post", counting_post)
    places.suggest_places("Karol Ba")
    places.suggest_places("karol ba")
    assert len(calls) == 1, "autocomplete runs per keystroke; repeats must not be billed twice"


def test_the_api_key_is_sent_as_a_header_not_a_query_parameter(monkeypatch):
    sent = {}

    def capturing_post(url, json=None, headers=None, timeout=None):
        sent["url"], sent["headers"] = url, headers
        response = Mock(status_code=200)
        response.json.return_value = OK_PAYLOAD
        return response

    monkeypatch.setattr(places.requests, "post", capturing_post)
    places.suggest_places("Karol Ba")
    assert SECRET not in sent["url"], "a key in the URL leaks into proxy and server logs"
    assert sent["headers"]["X-Goog-Api-Key"] == SECRET


def test_a_missing_key_is_a_configuration_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(places.PlacesError):
        places.suggest_places("Karol Ba")


@pytest.mark.parametrize("failure", [
    {"status_code": 403, "payload": {"error": {"message": f"key={SECRET} denied"}}},
    {"status_code": 500, "payload": {}},
    {"error": places.RequestException("boom")},
])
def test_a_provider_failure_never_leaks_the_key(monkeypatch, caplog, failure):
    respond(monkeypatch, **failure)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(places.PlacesError) as raised:
            places.suggest_places("Karol Ba")
    assert SECRET not in str(raised.value)
    assert SECRET not in caplog.text


def test_a_non_json_body_is_reported_as_unavailable(monkeypatch):
    def bad_post(url, json=None, headers=None, timeout=None):
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("not json")
        return response

    monkeypatch.setattr(places.requests, "post", bad_post)
    with pytest.raises(places.PlacesError):
        places.suggest_places("Karol Ba")


def test_malformed_predictions_are_dropped_rather_than_returned_half_built(monkeypatch):
    respond(monkeypatch, payload={"suggestions": [
        {"placePrediction": {"text": {"text": "Good"}, "placeId": "abc"}},
        {"placePrediction": {"text": {"text": ""}, "placeId": "no-description"}},
        {"placePrediction": {"text": {"text": "No id"}}},
        {"queryPrediction": {"text": {"text": "Not a place"}}},
    ]})
    assert places.suggest_places("Karol Ba") == [{"description": "Good", "place_id": "abc"}]


def test_the_suggestion_list_is_capped(monkeypatch):
    many = [{"placePrediction": {"text": {"text": f"Place {n}"}, "placeId": f"id{n}"}}
            for n in range(40)]
    respond(monkeypatch, payload={"suggestions": many})
    assert len(places.suggest_places("Karol Ba")) <= places.MAX_SUGGESTIONS


def test_an_overlong_query_is_rejected(monkeypatch):
    respond(monkeypatch, payload=OK_PAYLOAD)
    with pytest.raises(places.PlacesError):
        places.suggest_places("x" * (places.MAX_QUERY_LENGTH + 1))


def test_the_suggest_route_returns_the_descriptions(monkeypatch):
    response = client(monkeypatch, payload=OK_PAYLOAD).get(
        "/api/places/suggest", params={"q": "Karol Ba"})
    assert response.status_code == 200
    assert response.json()["suggestions"][0]["place_id"] == "ChIJ0y5AX5wCDTkRRtmdTCl0IZQ"


def test_the_suggest_route_reports_an_outage_as_bad_gateway(monkeypatch):
    response = client(monkeypatch, status_code=500, payload={}).get(
        "/api/places/suggest", params={"q": "Karol Ba"})
    assert response.status_code == 502
    assert SECRET not in response.text


def test_the_suggest_route_returns_an_empty_list_for_a_short_query(monkeypatch):
    response = client(monkeypatch, payload=OK_PAYLOAD).get(
        "/api/places/suggest", params={"q": "Ka"})
    assert response.status_code == 200
    assert response.json()["suggestions"] == []
