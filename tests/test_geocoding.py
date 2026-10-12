"""Location search by place name (STORY-049).

The security property under test is that GOOGLE_MAPS_API_KEY never reaches a
caller, a log line, or an error body — geocoding is a backend concern precisely
so the browser never holds the key.
"""

import importlib
import logging
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

geocoding = importlib.import_module("tools.geocoding_service")

SECRET = "AIzaSy-this-is-the-secret-key-value"

OK_PAYLOAD = {
    "status": "OK",
    "results": [{
        "geometry": {"location": {"lat": 1.3136, "lng": 103.656}},
        "formatted_address": "11B Tuas Rd, Jurong Industrial Estate, Singapore",
    }],
}


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    geocoding._cache.clear()
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", SECRET)
    yield
    geocoding._cache.clear()


def respond(monkeypatch, *, status_code=200, payload=None, error=None):
    def fake_get(url, params=None, timeout=None):
        if error is not None:
            raise error
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        return response
    monkeypatch.setattr(geocoding.requests, "get", fake_get)


def test_a_place_name_resolves_to_coordinates(monkeypatch):
    respond(monkeypatch, payload=OK_PAYLOAD)
    place = geocoding.geocode_place("Jurong Industrial Estate Singapore")
    assert place["lat"] == pytest.approx(1.3136)
    assert place["lng"] == pytest.approx(103.656)
    assert "Jurong" in place["formatted_address"]


def test_repeat_searches_are_served_from_cache(monkeypatch):
    calls = []

    def counting_get(url, params=None, timeout=None):
        calls.append(params)
        response = Mock(status_code=200)
        response.json.return_value = OK_PAYLOAD
        return response

    monkeypatch.setattr(geocoding.requests, "get", counting_get)
    geocoding.geocode_place("Singapore")
    geocoding.geocode_place("  singapore  ")  # same place, different spacing/case
    assert len(calls) == 1


def test_no_match_is_distinct_from_an_outage(monkeypatch):
    respond(monkeypatch, payload={"status": "ZERO_RESULTS", "results": []})
    with pytest.raises(geocoding.GeocodingNoMatch):
        geocoding.geocode_place("Nonexistentplacexyz")


@pytest.mark.parametrize("payload", [
    {"status": "REQUEST_DENIED", "error_message": f"The key {SECRET} is invalid"},
    {"status": "OVER_QUERY_LIMIT"},
    {"status": "OK", "results": []},
    {"status": "OK", "results": [{"geometry": {"location": {"lat": 999, "lng": 0}}}]},
    {"status": "OK", "results": [{"geometry": {}}]},
])
def test_unusable_responses_raise_a_generic_error(monkeypatch, payload):
    respond(monkeypatch, payload=payload)
    with pytest.raises(geocoding.GeocodingError) as caught:
        geocoding.geocode_place("anywhere")
    assert SECRET not in str(caught.value), "the key must never reach a caller"


def test_upstream_error_message_containing_the_key_is_not_logged(monkeypatch, caplog):
    respond(monkeypatch, payload={"status": "REQUEST_DENIED", "error_message": f"key {SECRET} bad"})
    with caplog.at_level(logging.WARNING):
        with pytest.raises(geocoding.GeocodingError):
            geocoding.geocode_place("anywhere")
    assert SECRET not in caplog.text, "Google echoes the key back; it must not be logged"


def test_transport_failure_degrades_to_a_generic_message(monkeypatch):
    respond(monkeypatch, error=geocoding.RequestException("boom"))
    with pytest.raises(geocoding.GeocodingError) as caught:
        geocoding.geocode_place("Singapore")
    assert str(caught.value) == geocoding.UNAVAILABLE_MESSAGE


def test_missing_key_is_a_configuration_error_not_a_crash(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(geocoding.GeocodingError):
        geocoding.geocode_place("Singapore")


@pytest.mark.parametrize("query", ["", "   ", "\n\t", "x" * 201])
def test_unusable_queries_are_rejected_before_any_request(monkeypatch, query):
    def forbidden(*args, **kwargs):
        raise AssertionError("an unusable query must not reach the Maps API")
    monkeypatch.setattr(geocoding.requests, "get", forbidden)
    with pytest.raises(geocoding.GeocodingError):
        geocoding.geocode_place(query)


# --- API route -------------------------------------------------------------

def client(monkeypatch, **kwargs):
    import main
    respond(monkeypatch, **kwargs)
    return TestClient(main.app)


def test_route_returns_the_resolved_place(monkeypatch):
    response = client(monkeypatch, payload=OK_PAYLOAD).get("/api/geocode", params={"q": "Jurong"})
    assert response.status_code == 200
    assert response.json()["lat"] == pytest.approx(1.3136)


def test_route_reports_no_match_as_404(monkeypatch):
    response = client(monkeypatch, payload={"status": "ZERO_RESULTS", "results": []}).get(
        "/api/geocode", params={"q": "Nonexistentplacexyz"})
    assert response.status_code == 404


def test_route_reports_an_outage_as_502_without_leaking_the_key(monkeypatch):
    response = client(monkeypatch, payload={
        "status": "REQUEST_DENIED", "error_message": f"key {SECRET} invalid"}).get(
        "/api/geocode", params={"q": "Singapore"})
    assert response.status_code == 502
    assert SECRET not in response.text


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "x" * 201}])
def test_route_rejects_unusable_queries(monkeypatch, params):
    assert client(monkeypatch, payload=OK_PAYLOAD).get("/api/geocode", params=params).status_code == 422
