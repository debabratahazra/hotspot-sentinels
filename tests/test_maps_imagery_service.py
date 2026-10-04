import struct
from unittest.mock import Mock

import pytest

from tools import maps_imagery_service as imagery_service


@pytest.fixture(autouse=True)
def reset_maps_process_state():
    with imagery_service._cache_lock:
        imagery_service._cache.clear()
        imagery_service._cache_bytes = 0
        imagery_service._request_timestamps.clear()


def png_header(width=640, height=640):
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", width, height)


def successful_response(content=None, content_type="image/png"):
    return Mock(
        status_code=200,
        headers={"Content-Type": content_type},
        content=png_header() if content is None else content,
    )


def test_cache_miss_requests_are_allowed_up_to_configured_limit(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_LIMIT", "2")
    response = successful_response()
    request = Mock(return_value=response)
    monkeypatch.setattr(imagery_service.requests, "get", request)

    imagery_service.fetch_satellite_imagery(1.0, 2.0)
    imagery_service.fetch_satellite_imagery(1.0, 2.001)

    assert request.call_count == 2
    assert len(imagery_service._request_timestamps) == 2


def test_cache_hits_do_not_spend_maps_request_allowance(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_LIMIT", "1")
    request = Mock(return_value=successful_response())
    monkeypatch.setattr(imagery_service.requests, "get", request)

    imagery_service.fetch_satellite_imagery(1.0, 2.0)
    cached = imagery_service.fetch_satellite_imagery(1.0, 2.0)

    assert cached["image_bytes"] == png_header()
    request.assert_called_once()
    assert len(imagery_service._request_timestamps) == 1


def test_exhausted_budget_rejects_cache_miss_without_outbound_call(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_LIMIT", "1")
    request = Mock(return_value=successful_response())
    monkeypatch.setattr(imagery_service.requests, "get", request)
    imagery_service.fetch_satellite_imagery(1.0, 2.0)
    request.reset_mock()

    with pytest.raises(imagery_service.MapsImageryRateLimitError):
        imagery_service.fetch_satellite_imagery(1.0, 2.001)

    request.assert_not_called()


def test_request_allowance_resets_after_rolling_window(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_LIMIT", "1")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_WINDOW_SECONDS", "10")
    now = [100.0]
    monkeypatch.setattr(imagery_service.time, "monotonic", lambda: now[0])
    request = Mock(return_value=successful_response())
    monkeypatch.setattr(imagery_service.requests, "get", request)
    imagery_service.fetch_satellite_imagery(1.0, 2.0)

    now[0] = 109.0
    with pytest.raises(imagery_service.MapsImageryRateLimitError):
        imagery_service.fetch_satellite_imagery(1.0, 2.001)
    assert request.call_count == 1

    now[0] = 110.0
    imagery_service.fetch_satellite_imagery(1.0, 2.001)
    assert request.call_count == 2


@pytest.mark.parametrize("lat,lng", [
    (91, 0), (0, 181), (float("nan"), 0), (0, float("inf")),
    ("1", 0), (True, 0),
])
def test_invalid_coordinates_are_rejected_before_request(monkeypatch, lat, lng):
    request = Mock()
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="valid coordinates"):
        imagery_service.fetch_satellite_imagery(lat, lng)

    request.assert_not_called()


def test_missing_maps_key_fails_before_request(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    request = Mock()
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="not configured"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    request.assert_not_called()


def test_provider_request_failure_is_wrapped_without_raw_details(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(side_effect=imagery_service.RequestException("qa-provider-secret"))
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="source is unavailable"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    assert "qa-provider-secret" not in caplog.text
    request.assert_called_once()


def test_provider_status_must_be_successful(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(return_value=Mock(status_code=403, headers={}, content=b"private payload"))
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="source is unavailable"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    request.assert_called_once()


def test_provider_content_type_must_be_png(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(return_value=successful_response(content_type="image/jpeg"))
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="invalid image"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    request.assert_called_once()


def test_provider_png_signature_must_be_valid(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(return_value=successful_response(content=b"not a png" + b"\x00" * 16))
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="invalid image"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    request.assert_called_once()


def test_provider_png_dimensions_must_be_640_by_640(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(return_value=successful_response(content=png_header(639, 640)))
    monkeypatch.setattr(imagery_service.requests, "get", request)

    with pytest.raises(imagery_service.MapsImageryError, match="invalid image"):
        imagery_service.fetch_satellite_imagery(1.0, 2.0)

    request.assert_called_once()


def test_cached_imagery_lookup_returns_cached_bytes(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    request = Mock(return_value=successful_response())
    monkeypatch.setattr(imagery_service.requests, "get", request)
    imagery_service.fetch_satellite_imagery(1.0, 2.0)

    cached = imagery_service.get_cached_satellite_imagery(1.0, 2.0)

    assert cached["image_bytes"] == png_header()
    assert cached["coordinate"] == {"lat": 1.0, "lng": 2.0}
    request.assert_called_once()


def test_cached_imagery_lookup_rejects_cache_miss():
    with pytest.raises(imagery_service.MapsImageryError, match="source is unavailable"):
        imagery_service.get_cached_satellite_imagery(1.0, 2.0)


def test_large_image_is_returned_without_entering_cache(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "offline-test-key")
    monkeypatch.setattr(imagery_service, "MAX_CACHE_BYTES", 1)
    request = Mock(return_value=successful_response())
    monkeypatch.setattr(imagery_service.requests, "get", request)

    first = imagery_service.fetch_satellite_imagery(1.0, 2.0)
    second = imagery_service.fetch_satellite_imagery(1.0, 2.0)

    assert first["image_bytes"] == second["image_bytes"] == png_header()
    assert request.call_count == 2


def test_invalid_budget_configuration_uses_defaults(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_LIMIT", "invalid")
    monkeypatch.setenv("GOOGLE_MAPS_REQUEST_WINDOW_SECONDS", "0")

    assert imagery_service._positive_env_int(
        "GOOGLE_MAPS_REQUEST_LIMIT", imagery_service.DEFAULT_REQUEST_LIMIT
    ) == imagery_service.DEFAULT_REQUEST_LIMIT
    assert imagery_service._positive_env_int(
        "GOOGLE_MAPS_REQUEST_WINDOW_SECONDS", imagery_service.DEFAULT_REQUEST_WINDOW_SECONDS
    ) == imagery_service.DEFAULT_REQUEST_WINDOW_SECONDS