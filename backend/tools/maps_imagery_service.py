import logging
import math
import os
import struct
import time
from collections import OrderedDict, deque
from threading import RLock
from typing import TypedDict

import requests
from requests.exceptions import RequestException

MAPS_STATIC_API_URL = "https://maps.googleapis.com/maps/api/staticmap"
IMAGE_SIZE = "640x640"
DEFAULT_ZOOM = 19
REQUEST_TIMEOUT = (3.0, 15.0)
MAX_CACHE_ENTRIES = 64
MAX_CACHE_BYTES = 32 * 1024 * 1024
DEFAULT_REQUEST_LIMIT = 100
DEFAULT_REQUEST_WINDOW_SECONDS = 3600
SHARED_CACHE_PREFIX = "maps-imagery-cache"
SHARED_CACHE_MAX_AGE_SECONDS = 24 * 3600
UNAVAILABLE_MESSAGE = "Satellite imagery source is unavailable."
logger = logging.getLogger(__name__)
_cache: OrderedDict[tuple[float, float, int, str, str], tuple[bytes, str]] = OrderedDict()
_cache_bytes = 0
_cache_lock = RLock()
_request_timestamps: deque[float] = deque()
_storage_client = None


class MapsImageryError(RuntimeError):
    """Maps Static API configuration or imagery retrieval failed."""


class MapsImageryRateLimitError(MapsImageryError):
    """The per-process rolling-window Maps request allowance was exhausted."""


class MapsImagery(TypedDict):
    image_bytes: bytes
    mime_type: str
    coordinate: dict[str, float]
    zoom: int
    attribution_required: bool


def fetch_satellite_imagery(lat: float, lng: float) -> MapsImagery:
    """Fetch an intact, attributed 640x640 satellite PNG for a coordinate."""
    coordinate = _normalize_coordinate(lat, lng)
    cache_key = _cache_key(coordinate["lat"], coordinate["lng"])

    global _cache_bytes
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached is not None:
            _cache.move_to_end(cache_key)
            return _as_imagery(cached, coordinate)

        maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not maps_key:
            raise MapsImageryError("Maps imagery is not configured.")

        _consume_request_allowance(time.monotonic())
        try:
            response = requests.get(
                MAPS_STATIC_API_URL,
                params={
                    "center": f'{coordinate["lat"]},{coordinate["lng"]}',
                    "zoom": DEFAULT_ZOOM,
                    "size": IMAGE_SIZE,
                    "maptype": "satellite",
                    "key": maps_key,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException as error:
            logger.warning("Maps Static API request failed (%s)", type(error).__name__)
            raise MapsImageryError(UNAVAILABLE_MESSAGE) from None

        if response.status_code != 200:
            logger.warning("Maps Static API returned HTTP %d", response.status_code)
            raise MapsImageryError(UNAVAILABLE_MESSAGE)

        content_type = response.headers.get("Content-Type", "")
        mime_type = content_type.partition(";")[0].strip().lower()
        image_bytes = response.content
        if mime_type != "image/png" or not _is_640_png(image_bytes):
            logger.warning("Maps Static API returned invalid imagery (HTTP %d)", response.status_code)
            raise MapsImageryError("Satellite imagery source returned an invalid image.")

        if len(image_bytes) <= MAX_CACHE_BYTES:
            _cache[cache_key] = (image_bytes, mime_type)
            _cache_bytes += len(image_bytes)
            while len(_cache) > MAX_CACHE_ENTRIES or _cache_bytes > MAX_CACHE_BYTES:
                _, (evicted_bytes, _) = _cache.popitem(last=False)
                _cache_bytes -= len(evicted_bytes)

        _put_shared(cache_key, image_bytes, mime_type)
        return _as_imagery((image_bytes, mime_type), coordinate)


def get_cached_satellite_imagery(lat: float, lng: float) -> MapsImagery:
    """Return previously fetched imagery without making a billable Maps request."""
    coordinate = _normalize_coordinate(lat, lng)
    cache_key = _cache_key(coordinate["lat"], coordinate["lng"])
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached is not None:
            _cache.move_to_end(cache_key)
            return _as_imagery(cached, coordinate)

    # Cloud Run runs several instances and scales to zero, so the process cache is
    # cold far more often than the imagery is actually unavailable. Fall back to the
    # shared copy before telling the caller the image is gone.
    shared = _get_shared(cache_key)
    if shared is None:
        raise MapsImageryError(UNAVAILABLE_MESSAGE)

    image_bytes, mime_type = shared
    with _cache_lock:
        global _cache_bytes
        if cache_key not in _cache and len(image_bytes) <= MAX_CACHE_BYTES:
            _cache[cache_key] = shared
            _cache_bytes += len(image_bytes)
            while len(_cache) > MAX_CACHE_ENTRIES or _cache_bytes > MAX_CACHE_BYTES:
                _, (evicted_bytes, _) = _cache.popitem(last=False)
                _cache_bytes -= len(evicted_bytes)
    return _as_imagery(shared, coordinate)


def _get_storage_client():
    global _storage_client
    if _storage_client is None:
        from google.cloud import storage

        _storage_client = storage.Client()
    return _storage_client


def _shared_blob(cache_key: tuple[float, float, int, str, str]):
    """Resolve the deterministic shared-cache blob for a cache key, or None.

    The object name encodes every component of the key, so one coordinate can never
    be served imagery fetched for another.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        return None
    lat, lng, zoom, size, maptype = cache_key
    name = f"{SHARED_CACHE_PREFIX}/{maptype}/z{zoom}/{size}/{lat:.6f}_{lng:.6f}.png"
    return _get_storage_client().bucket(bucket_name).blob(name)


def _put_shared(cache_key: tuple[float, float, int, str, str], image_bytes: bytes, mime_type: str) -> None:
    """Publish imagery for other instances. A storage failure must not fail analysis."""
    try:
        blob = _shared_blob(cache_key)
        if blob is None:
            return
        blob.upload_from_string(image_bytes, content_type=mime_type)
    except Exception as error:  # noqa: BLE001 - the cache is strictly best-effort
        logger.warning("Shared imagery cache write failed (%s)", type(error).__name__)


def _get_shared(cache_key: tuple[float, float, int, str, str]) -> tuple[bytes, str] | None:
    try:
        blob = _shared_blob(cache_key)
        if blob is None:
            return None
        image_bytes = blob.download_as_bytes()
    except Exception as error:  # noqa: BLE001 - a miss and an outage are both "not cached"
        logger.warning("Shared imagery cache read failed (%s)", type(error).__name__)
        return None

    # Never hand back something that is not the imagery we stored.
    if not _is_640_png(image_bytes):
        logger.warning("Shared imagery cache entry was not a valid 640px PNG; ignoring")
        return None
    if _shared_entry_expired(blob):
        logger.info("Shared imagery cache entry is stale; ignoring")
        return None
    return image_bytes, "image/png"


def _shared_entry_expired(blob) -> bool:
    updated = getattr(blob, "updated", None)
    if updated is None:
        return False
    try:
        from datetime import datetime, timezone

        age = (datetime.now(timezone.utc) - updated).total_seconds()
    except (TypeError, ValueError):
        return False
    return age > SHARED_CACHE_MAX_AGE_SECONDS


def _normalize_coordinate(lat: float, lng: float) -> dict[str, float]:
    if (
        isinstance(lat, bool)
        or isinstance(lng, bool)
        or not isinstance(lat, (int, float))
        or not isinstance(lng, (int, float))
        or not -90 <= lat <= 90
        or not -180 <= lng <= 180
        or not math.isfinite(lat)
        or not math.isfinite(lng)
    ):
        raise MapsImageryError("Latitude and longitude must be finite, valid coordinates.")

    return {
        "lat": round(float(lat), 6) or 0.0,
        "lng": round(float(lng), 6) or 0.0,
    }


def _cache_key(lat: float, lng: float) -> tuple[float, float, int, str, str]:
    return lat, lng, DEFAULT_ZOOM, IMAGE_SIZE, "satellite"


def _consume_request_allowance(now: float) -> None:
    limit = _positive_env_int("GOOGLE_MAPS_REQUEST_LIMIT", DEFAULT_REQUEST_LIMIT)
    window_seconds = _positive_env_int(
        "GOOGLE_MAPS_REQUEST_WINDOW_SECONDS", DEFAULT_REQUEST_WINDOW_SECONDS
    )
    cutoff = now - window_seconds
    while _request_timestamps and _request_timestamps[0] <= cutoff:
        _request_timestamps.popleft()
    if len(_request_timestamps) >= limit:
        raise MapsImageryRateLimitError("Maps imagery request allowance is exhausted.")
    _request_timestamps.append(now)


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _as_imagery(
    cached: tuple[bytes, str], coordinate: dict[str, float]
) -> MapsImagery:
    image_bytes, mime_type = cached
    return {
        "image_bytes": image_bytes,
        "mime_type": mime_type,
        "coordinate": coordinate,
        "zoom": DEFAULT_ZOOM,
        "attribution_required": True,
    }


def _is_640_png(image_bytes: bytes) -> bool:
    return (
        len(image_bytes) >= 24
        and image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        and struct.unpack(">II", image_bytes[16:24]) == (640, 640)
    )