import logging
import math
import os
import time
from collections import OrderedDict
from threading import RLock
from typing import TypedDict

import requests
from requests.exceptions import RequestException

from tools.water_bodies import name_water_body

GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
REQUEST_TIMEOUT = (3.0, 10.0)
MAX_QUERY_LENGTH = 200
MAX_CACHE_ENTRIES = 256
CACHE_TTL_SECONDS = 24 * 3600
UNAVAILABLE_MESSAGE = "Location search is unavailable."
NO_MATCH_MESSAGE = "No place matched that search."
logger = logging.getLogger(__name__)
_cache: OrderedDict[str, tuple[float, "GeocodedPlace"]] = OrderedDict()
_cache_lock = RLock()


class GeocodingError(RuntimeError):
    """Geocoding configuration or lookup failed."""


class GeocodingNoMatch(GeocodingError):
    """The query was valid but matched no place."""


class GeocodedPlace(TypedDict):
    lat: float
    lng: float
    formatted_address: str


def geocode_place(query: str) -> GeocodedPlace:
    """Resolve a place name to coordinates, with a short-lived in-process cache."""
    cleaned = _clean_query(query)
    return _lookup({"address": cleaned}, cleaned.lower())


def geocode_place_id(place_id: str) -> GeocodedPlace:
    """Resolve an autocomplete suggestion to its exact coordinates."""
    cleaned = _clean_query(place_id)
    return _lookup({"place_id": cleaned}, f"place_id:{cleaned}")


def reverse_geocode(latitude: float, longitude: float) -> GeocodedPlace:
    """Name the place at a coordinate, so a map click reads as somewhere real."""
    if not _is_coordinate(latitude, -90, 90) or not _is_coordinate(longitude, -180, 180):
        raise GeocodingError("Coordinates are out of range.")
    latitude, longitude = round(float(latitude), 6), round(float(longitude), 6)
    cache_key = f"reverse:{latitude},{longitude}"

    cached = _cached(cache_key)
    if cached is not None:
        return cached

    geocoded = _request({"latlng": f"{latitude},{longitude}"})
    place: GeocodedPlace = {
        "lat": latitude,
        "lng": longitude,
        "formatted_address": _describe(geocoded, latitude, longitude),
    }
    return _store(cache_key, place)


def _lookup(query_params: dict, cache_key: str) -> GeocodedPlace:
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    return _store(cache_key, _first_place(_request(query_params)))


def _cached(cache_key: str) -> GeocodedPlace | None:
    with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is None:
            return None
        stored_at, place = entry
        if time.monotonic() - stored_at <= CACHE_TTL_SECONDS:
            _cache.move_to_end(cache_key)
            return place
        del _cache[cache_key]
        return None


def _store(cache_key: str, place: GeocodedPlace) -> GeocodedPlace:
    with _cache_lock:
        _cache[cache_key] = (time.monotonic(), place)
        while len(_cache) > MAX_CACHE_ENTRIES:
            _cache.popitem(last=False)
    return place


def _request(query_params: dict) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise GeocodingError("Location search is not configured.")

    try:
        response = requests.get(
            GEOCODE_API_URL,
            params={**query_params, "key": api_key},
            timeout=REQUEST_TIMEOUT,
        )
    except RequestException as error:
        logger.warning("Geocoding request failed (%s)", type(error).__name__)
        raise GeocodingError(UNAVAILABLE_MESSAGE) from None

    if response.status_code != 200:
        logger.warning("Geocoding returned HTTP %d", response.status_code)
        raise GeocodingError(UNAVAILABLE_MESSAGE)

    try:
        geocoded = response.json()
    except ValueError:
        logger.warning("Geocoding returned a non-JSON body")
        raise GeocodingError(UNAVAILABLE_MESSAGE) from None

    status = geocoded.get("status")
    if status == "ZERO_RESULTS":
        raise GeocodingNoMatch(NO_MATCH_MESSAGE)
    if status != "OK":
        # error_message can echo the key back; never let it reach a caller or a log.
        logger.warning("Geocoding status %s", status)
        raise GeocodingError(UNAVAILABLE_MESSAGE)
    return geocoded


def _describe(geocoded: dict, latitude: float, longitude: float) -> str:
    """Build a readable place name from the broadest useful address components."""
    components: dict[str, str] = {}
    for result in geocoded.get("results") or []:
        for component in result.get("address_components") or []:
            name = component.get("long_name")
            if not name:
                continue
            for component_type in component.get("types") or []:
                components.setdefault(component_type, name)

    country = components.get("country")
    if not country:
        # At sea Google still answers OK, but with a Plus Code and no country.
        return name_water_body(latitude, longitude)

    for key in ("locality", "postal_town", "administrative_area_level_2",
                "administrative_area_level_1"):
        area = components.get(key)
        if area and area != country:
            return f"{area}, {country}"
    return country


def _clean_query(query: str) -> str:
    if not isinstance(query, str):
        raise GeocodingError("Search text must be a string.")
    cleaned = " ".join(query.split())
    if not cleaned:
        raise GeocodingError("Enter a place to search for.")
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise GeocodingError("Search text is too long.")
    return cleaned


def _first_place(geocoded: dict) -> GeocodedPlace:
    results = geocoded.get("results") or []
    if not results:
        raise GeocodingNoMatch(NO_MATCH_MESSAGE)
    location = ((results[0].get("geometry") or {}).get("location")) or {}
    latitude, longitude = location.get("lat"), location.get("lng")
    if not _is_coordinate(latitude, -90, 90) or not _is_coordinate(longitude, -180, 180):
        logger.warning("Geocoding returned an unusable location")
        raise GeocodingError(UNAVAILABLE_MESSAGE)
    address = results[0].get("formatted_address")
    return {
        "lat": round(float(latitude), 6),
        "lng": round(float(longitude), 6),
        "formatted_address": str(address) if address else "Unnamed location",
    }


def _is_coordinate(value, low: float, high: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and low <= value <= high
    )
