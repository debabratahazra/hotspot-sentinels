"""Cross-instance imagery cache (TASK-046).

A second Cloud Run instance is simulated by clearing the process cache, which is
exactly what a cold container starts with. Everything here is offline: the storage
client is replaced with an in-memory double.
"""

import importlib
from datetime import datetime, timedelta, timezone

import pytest

maps = importlib.import_module("tools.maps_imagery_service")


class FakeBlob:
    def __init__(self, store: dict, name: str):
        self._store = store
        self.name = name

    def upload_from_string(self, data: bytes, content_type: str = "") -> None:
        self._store[self.name] = (data, content_type, datetime.now(timezone.utc))

    def download_as_bytes(self) -> bytes:
        if self.name not in self._store:
            raise FileNotFoundError(self.name)
        return self._store[self.name][0]

    @property
    def updated(self):
        entry = self._store.get(self.name)
        return entry[2] if entry else None


class FakeBucket:
    def __init__(self, store: dict):
        self._store = store

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self._store, name)


class FakeStorageClient:
    def __init__(self, store: dict):
        self._store = store

    def bucket(self, _name: str) -> FakeBucket:
        return FakeBucket(self._store)


@pytest.fixture
def shared_store(monkeypatch):
    store: dict = {}
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(maps, "_get_storage_client", lambda: FakeStorageClient(store))
    maps._cache.clear()
    monkeypatch.setattr(maps, "_cache_bytes", 0, raising=False)
    yield store
    maps._cache.clear()


def png_640() -> bytes:
    """A PNG header the service accepts as 640x640, plus filler."""
    import struct

    ihdr = struct.pack(">II", 640, 640) + bytes([8, 2, 0, 0, 0])
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + ihdr
        + b"\x00\x00\x00\x00"
        + b"\x00" * 64
    )


def simulate_other_instance():
    """A cold container has an empty process cache and nothing else."""
    maps._cache.clear()


def test_image_cached_by_one_instance_is_served_by_another(shared_store, monkeypatch):
    key = maps._cache_key(1.2897, 103.754)
    maps._put_shared(key, png_640(), "image/png")
    assert shared_store, "the first instance must publish to the shared cache"

    simulate_other_instance()
    result = maps.get_cached_satellite_imagery(1.2897, 103.754)
    assert result["image_bytes"] == png_640()
    assert result["attribution_required"] is True


def test_cross_instance_hit_makes_no_maps_request(shared_store, monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("a cross-instance cache hit must not call the Maps API")

    monkeypatch.setattr(maps.requests, "get", forbidden)
    maps._put_shared(maps._cache_key(1.3521, 103.8198), png_640(), "image/png")
    simulate_other_instance()
    assert maps.get_cached_satellite_imagery(1.3521, 103.8198)["image_bytes"] == png_640()


def test_shared_miss_is_an_explicit_error_not_unrelated_bytes(shared_store):
    maps._put_shared(maps._cache_key(1.2897, 103.754), png_640(), "image/png")
    simulate_other_instance()
    # A different coordinate must not be served the first coordinate's imagery.
    with pytest.raises(maps.MapsImageryError):
        maps.get_cached_satellite_imagery(40.0, -74.0)


def test_expired_shared_entry_is_ignored(shared_store, monkeypatch):
    key = maps._cache_key(1.2897, 103.754)
    maps._put_shared(key, png_640(), "image/png")
    name = next(iter(shared_store))
    data, ctype, _ = shared_store[name]
    stale = datetime.now(timezone.utc) - timedelta(seconds=maps.SHARED_CACHE_MAX_AGE_SECONDS + 60)
    shared_store[name] = (data, ctype, stale)

    simulate_other_instance()
    with pytest.raises(maps.MapsImageryError):
        maps.get_cached_satellite_imagery(1.2897, 103.754)


def test_corrupt_shared_entry_is_never_served(shared_store):
    key = maps._cache_key(1.2897, 103.754)
    maps._put_shared(key, png_640(), "image/png")
    name = next(iter(shared_store))
    _, ctype, when = shared_store[name]
    shared_store[name] = (b"not a png at all", ctype, when)

    simulate_other_instance()
    with pytest.raises(maps.MapsImageryError):
        maps.get_cached_satellite_imagery(1.2897, 103.754)


def test_storage_failure_degrades_instead_of_breaking_analysis(monkeypatch):
    maps._cache.clear()

    class Exploding:
        def bucket(self, _name):
            raise RuntimeError("storage is down")

    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(maps, "_get_storage_client", lambda: Exploding())

    # A write failure must not propagate: analysis continues without the shared copy.
    maps._put_shared(maps._cache_key(1.0, 2.0), png_640(), "image/png")
    # A read failure is indistinguishable from a miss, and must be an explicit error.
    with pytest.raises(maps.MapsImageryError):
        maps.get_cached_satellite_imagery(1.0, 2.0)


def test_shared_cache_is_skipped_when_no_bucket_is_configured(monkeypatch):
    maps._cache.clear()
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)

    def forbidden():
        raise AssertionError("no bucket configured means no storage client is built")

    monkeypatch.setattr(maps, "_get_storage_client", forbidden)
    maps._put_shared(maps._cache_key(1.0, 2.0), png_640(), "image/png")
    with pytest.raises(maps.MapsImageryError):
        maps.get_cached_satellite_imagery(1.0, 2.0)


def test_local_cache_hit_does_not_touch_storage(shared_store, monkeypatch):
    key = maps._cache_key(1.2897, 103.754)
    maps._cache[key] = (png_640(), "image/png")

    def forbidden(*_a, **_k):
        raise AssertionError("a local hit must not reach the shared cache")

    monkeypatch.setattr(maps, "_get_shared", forbidden)
    assert maps.get_cached_satellite_imagery(1.2897, 103.754)["image_bytes"] == png_640()
