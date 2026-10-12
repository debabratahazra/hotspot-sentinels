"""Naming the place behind a map click (STORY-054, STORY-055).

The behaviour that matters is that a click never shows a Plus Code and never
shows nothing: every point on earth resolves to a name an operator can read.
"""

import importlib
import logging
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

geocoding = importlib.import_module("tools.geocoding_service")
water = importlib.import_module("tools.water_bodies")

SECRET = "AIzaSy-this-is-the-secret-key-value"


def components(*pairs):
    return [{"long_name": name, "types": [kind]} for kind, name in pairs]


CITY = {"status": "OK", "results": [{
    "formatted_address": "6/24, Block 51, WEA, Karol Bagh, New Delhi, Delhi, 110005, India",
    "address_components": components(
        ("locality", "New Delhi"), ("administrative_area_level_1", "Delhi"), ("country", "India")),
}]}
# Google answers OK over water, but with a Plus Code and no components at all.
AT_SEA = {"status": "OK", "results": [{"formatted_address": "63GG2222+22", "address_components": []}]}


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


def client(monkeypatch, **kwargs):
    respond(monkeypatch, **kwargs)
    main = importlib.import_module("main")
    return TestClient(main.app)


def test_a_click_in_a_city_names_the_city_and_country(monkeypatch):
    respond(monkeypatch, payload=CITY)
    assert geocoding.reverse_geocode(28.655, 77.1888)["formatted_address"] == "New Delhi, India"


def test_remote_land_falls_back_to_the_region_and_country(monkeypatch):
    respond(monkeypatch, payload={"status": "OK", "results": [{
        "formatted_address": "7GM72222+22",
        "address_components": components(
            ("administrative_area_level_1", "The New Valley Governorate"), ("country", "Egypt")),
    }]})
    assert geocoding.reverse_geocode(23.0, 25.0)["formatted_address"] == \
        "The New Valley Governorate, Egypt"


def test_a_country_with_no_smaller_area_is_named_alone(monkeypatch):
    respond(monkeypatch, payload={"status": "OK", "results": [{
        "formatted_address": "2FG22222+22",
        "address_components": components(("country", "Antarctica")),
    }]})
    assert geocoding.reverse_geocode(-80.0, 0.0)["formatted_address"] == "Antarctica"


def test_a_city_state_is_not_named_twice(monkeypatch):
    respond(monkeypatch, payload={"status": "OK", "results": [{
        "formatted_address": "7QQ3+VJ Singapore",
        "address_components": components(("locality", "Singapore"), ("country", "Singapore")),
    }]})
    assert geocoding.reverse_geocode(1.2897, 103.754)["formatted_address"] == "Singapore"


@pytest.mark.parametrize("latitude,longitude,expected", [
    (35.0, 18.0, "Mediterranean Sea"),
    (0.0, -150.0, "Pacific Ocean"),
    (13.0, 115.0, "South China Sea"),
])
def test_a_click_at_sea_is_named_from_the_water_table(monkeypatch, latitude, longitude, expected):
    respond(monkeypatch, payload=AT_SEA)
    assert geocoding.reverse_geocode(latitude, longitude)["formatted_address"] == expected


def test_a_plus_code_is_never_shown(monkeypatch):
    respond(monkeypatch, payload=AT_SEA)
    assert "+" not in geocoding.reverse_geocode(35.0, 18.0)["formatted_address"]


def test_a_repeat_click_on_the_same_point_is_served_from_cache(monkeypatch):
    calls = []

    def counting_get(url, params=None, timeout=None):
        calls.append(params)
        response = Mock(status_code=200)
        response.json.return_value = CITY
        return response

    monkeypatch.setattr(geocoding.requests, "get", counting_get)
    geocoding.reverse_geocode(28.655, 77.1888)
    geocoding.reverse_geocode(28.655, 77.1888)
    assert len(calls) == 1


def test_an_out_of_range_coordinate_is_refused_before_any_request(monkeypatch):
    called = []
    monkeypatch.setattr(geocoding.requests, "get",
                        lambda *a, **k: called.append(1) or Mock(status_code=200))
    with pytest.raises(geocoding.GeocodingError):
        geocoding.reverse_geocode(91.0, 0.0)
    assert not called


def test_a_failure_never_leaks_the_key(monkeypatch, caplog):
    respond(monkeypatch, status_code=403,
            payload={"status": "REQUEST_DENIED", "error_message": f"key={SECRET}"})
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(geocoding.GeocodingError) as raised:
            geocoding.reverse_geocode(28.655, 77.1888)
    assert SECRET not in str(raised.value)
    assert SECRET not in caplog.text


def test_the_reverse_route_returns_the_name(monkeypatch):
    response = client(monkeypatch, payload=CITY).get(
        "/api/geocode/reverse", params={"lat": 28.655, "lng": 77.1888})
    assert response.status_code == 200
    assert response.json()["formatted_address"] == "New Delhi, India"


def test_the_reverse_route_echoes_the_coordinate_it_was_given(monkeypatch):
    # The caller plots this point, so it must not drift to the geocoder's own.
    response = client(monkeypatch, payload=CITY).get(
        "/api/geocode/reverse", params={"lat": 28.655, "lng": 77.1888})
    assert (response.json()["lat"], response.json()["lng"]) == (28.655, 77.1888)


@pytest.mark.parametrize("params", [
    {"lat": 91, "lng": 0}, {"lat": 0, "lng": 181}, {"lat": "x", "lng": 0}, {"lat": 0},
])
def test_the_reverse_route_rejects_unusable_coordinates(monkeypatch, params):
    assert client(monkeypatch, payload=CITY).get(
        "/api/geocode/reverse", params=params).status_code == 422


def test_the_reverse_route_reports_an_outage_as_bad_gateway(monkeypatch):
    response = client(monkeypatch, status_code=500, payload={}).get(
        "/api/geocode/reverse", params={"lat": 1.0, "lng": 1.0})
    assert response.status_code == 502
    assert SECRET not in response.text


@pytest.mark.parametrize("latitude,longitude,expected", [
    (35.0, 18.0, "Mediterranean Sea"),
    (44.0, 34.0, "Black Sea"),
    (20.0, 38.0, "Red Sea"),
    (15.0, 65.0, "Arabian Sea"),
    (15.0, 88.0, "Bay of Bengal"),
    (10.0, 95.0, "Andaman Sea"),
    (13.0, 115.0, "South China Sea"),
    (15.0, -75.0, "Caribbean Sea"),
    (25.0, -90.0, "Gulf of Mexico"),
    (56.0, 3.0, "North Sea"),
    (-70.0, 0.0, "Southern Ocean"),
    (80.0, 0.0, "Arctic Ocean"),
    (-20.0, 80.0, "Indian Ocean"),
    (0.0, -150.0, "Pacific Ocean"),
    (0.0, 170.0, "Pacific Ocean"),
    (-30.0, -30.0, "Atlantic Ocean"),
])
def test_every_sea_and_ocean_in_the_table_is_reachable(latitude, longitude, expected):
    assert water.name_water_body(latitude, longitude) == expected


def test_an_enclosed_sea_wins_over_the_ocean_containing_it():
    # The Mediterranean sits inside the Atlantic's longitude band; order decides.
    assert water.name_water_body(35.0, 18.0) == "Mediterranean Sea"
    assert water.name_water_body(10.0, 95.0) == "Andaman Sea"


def test_no_sea_is_shadowed_by_an_earlier_entry():
    # The Black Sea sits inside the Mediterranean's box and was returned as the
    # Mediterranean until it was ordered first. Any entry whose own centre
    # resolves to a different name is unreachable in the same way.
    for name, lat_min, lat_max, lng_min, lng_max in water.SEAS:
        centre = ((lat_min + lat_max) / 2, (lng_min + lng_max) / 2)
        assert water.name_water_body(*centre) == name, (
            f"{name} is shadowed at its own centre; move it earlier in SEAS"
        )


def test_every_point_on_earth_gets_a_name():
    for latitude in range(-90, 91, 10):
        for longitude in range(-180, 181, 10):
            name = water.name_water_body(float(latitude), float(longitude))
            assert name and isinstance(name, str)
