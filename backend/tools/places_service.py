"""Place suggestions for the dashboard's typeahead.

Proxies Google Places Autocomplete so GOOGLE_MAPS_API_KEY stays in the backend.
Suggestions carry a place_id rather than coordinates; the caller resolves that
through geocoding_service, which keeps one coordinate path for the whole app.
"""

import logging
import os
import time
from collections import OrderedDict
from threading import RLock
from typing import TypedDict

import requests
from requests.exceptions import RequestException

AUTOCOMPLETE_API_URL = "https://places.googleapis.com/v1/places:autocomplete"
REQUEST_TIMEOUT = (3.0, 10.0)
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 200
MAX_SUGGESTIONS = 8
MAX_CACHE_ENTRIES = 256
CACHE_TTL_SECONDS = 3600
UNAVAILABLE_MESSAGE = "Place suggestions are unavailable."
logger = logging.getLogger(__name__)
_cache: OrderedDict[str, tuple[float, list["PlaceSuggestion"]]] = OrderedDict()
_cache_lock = RLock()


class PlacesError(RuntimeError):
    """Place suggestion configuration or lookup failed."""


class PlaceSuggestion(TypedDict):
    description: str
    place_id: str


def suggest_places(query: str) -> list[PlaceSuggestion]:
    """Suggest places for a partial name. Short queries cost nothing."""
    cleaned = _clean_query(query)
    if len(cleaned) < MIN_QUERY_LENGTH:
        return []

    cache_key = cleaned.lower()
    with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is not None:
            stored_at, suggestions = entry
            if time.monotonic() - stored_at <= CACHE_TTL_SECONDS:
                _cache.move_to_end(cache_key)
                return suggestions
            del _cache[cache_key]

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise PlacesError("Place search is not configured.")

    try:
        response = requests.post(
            AUTOCOMPLETE_API_URL,
            json={"input": cleaned},
            headers={"X-Goog-Api-Key": api_key, "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
    except RequestException as error:
        logger.warning("Place suggestion request failed (%s)", type(error).__name__)
        raise PlacesError(UNAVAILABLE_MESSAGE) from None

    if response.status_code != 200:
        # The error body can quote the request, key included; log only the code.
        logger.warning("Place suggestions returned HTTP %d", response.status_code)
        raise PlacesError(UNAVAILABLE_MESSAGE)

    try:
        suggested = response.json()
    except ValueError:
        logger.warning("Place suggestions returned a non-JSON body")
        raise PlacesError(UNAVAILABLE_MESSAGE) from None

    suggestions = _parse_suggestions(suggested)
    with _cache_lock:
        _cache[cache_key] = (time.monotonic(), suggestions)
        while len(_cache) > MAX_CACHE_ENTRIES:
            _cache.popitem(last=False)
    return suggestions


def _clean_query(query: str) -> str:
    if not isinstance(query, str):
        raise PlacesError("Search text must be a string.")
    cleaned = " ".join(query.split())
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise PlacesError("Search text is too long.")
    return cleaned


def _parse_suggestions(suggested: dict) -> list[PlaceSuggestion]:
    places: list[PlaceSuggestion] = []
    for item in (suggested.get("suggestions") or [])[:MAX_SUGGESTIONS]:
        prediction = item.get("placePrediction") or {}
        description = ((prediction.get("text") or {}).get("text") or "").strip()
        place_id = str(prediction.get("placeId") or "").strip()
        if description and place_id:
            places.append({"description": description, "place_id": place_id})
    return places
