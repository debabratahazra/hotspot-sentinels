import hashlib
import json
import logging
import os
from concurrent.futures import TimeoutError
from datetime import datetime, timezone
from threading import Lock

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.publisher.exceptions import MessageTooLargeError
from grpc import RpcError
from requests.exceptions import RequestException

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID", "heat-resilience-alerts")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1")
UTC_OFFSET = "+00:00"
FAILURE_MESSAGE = "Heat alert dispatch failed: %s"
logger = logging.getLogger(__name__)
_client = None
_client_lock = Lock()


def _get_client() -> pubsub_v1.PublisherClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = pubsub_v1.PublisherClient()
        return _client


def _bounded_text(value: object, max_bytes: int) -> str:
    if not isinstance(value, str) or len(value) > max_bytes:
        raise ValueError
    if not value.strip() or len(value.encode("utf-8")) > max_bytes:
        raise ValueError
    return value


def _metric_number(value: object, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError
    if not minimum <= value <= maximum:
        raise ValueError
    return float(value)


def _build_alert(zone_data: dict) -> dict:
    zone_id = _bounded_text(zone_data.get("zone_id"), 128)
    zone_name = _bounded_text(zone_data.get("zone_name", "Unknown"), 256)
    coordinates = zone_data.get("coordinates")
    plan = zone_data.get("passive_cooling_plan")
    if not isinstance(coordinates, dict) or not isinstance(plan, dict):
        raise ValueError
    interventions = plan.get("micro_canopy_interventions")
    if not isinstance(interventions, list) or not 1 <= len(interventions) <= 5:
        raise ValueError
    urgent_interventions = [_bounded_text(action, 512) for action in interventions]
    timestamp = _bounded_text(zone_data.get("timestamp"), 64)
    scan_time = datetime.fromisoformat(timestamp.replace("Z", UTC_OFFSET))
    if scan_time.tzinfo is None:
        raise ValueError
    timestamp = scan_time.astimezone(timezone.utc).isoformat().replace(UTC_OFFSET, "Z")
    identity = json.dumps([zone_id, timestamp], ensure_ascii=True).encode("utf-8")
    return {
        "schema_version": 1,
        "event_id": hashlib.sha256(identity).hexdigest(),
        "zone_id": zone_id,
        "zone_name": zone_name,
        "coordinates": {
            "lat": _metric_number(coordinates.get("lat"), -90, 90),
            "lng": _metric_number(coordinates.get("lng"), -180, 180),
        },
        "ambient_temp_c": _metric_number(zone_data.get("ambient_temp_c"), -50, 60),
        "hvi_score": _metric_number(zone_data.get("hvi_score"), 1, 10),
        "risk_level": "CRITICAL",
        "timestamp": timestamp,
        "dispatched_at": datetime.now(timezone.utc).isoformat().replace(UTC_OFFSET, "Z"),
        "headline_intervention": urgent_interventions[0],
        "urgent_interventions": urgent_interventions,
    }


def dispatch_heat_alert(zone_data: dict) -> str:
    """Publish a bounded critical event; invalid reports and cloud failures return ''.

    Risk classification belongs to the analyzer. Subscribers can deduplicate on
    event_id (zone ID plus UTC scan time), never the per-attempt dispatched_at.
    Only allowlisted operational fields are sent, not report extras or imagery.
    """
    if not isinstance(zone_data, dict):
        logger.log(logging.ERROR, FAILURE_MESSAGE, ValueError.__name__)
        return ""
    if zone_data.get("risk_level") != "CRITICAL":
        return ""
    try:
        event = _build_alert(zone_data)
        region = _bounded_text(REGION, 64)
    except (ValueError, OverflowError) as error:
        logger.log(logging.ERROR, FAILURE_MESSAGE, type(error).__name__)
        return ""
    try:
        publisher = _get_client()
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
        data_bytes = json.dumps(event, ensure_ascii=False, allow_nan=False).encode("utf-8")
        future = publisher.publish(
            topic_path,
            data_bytes,
            alert_type="CRITICAL_HEAT",
            zone=event["zone_name"],
            zone_id=event["zone_id"],
            risk_level=event["risk_level"],
            region=region,
        )
        return future.result(timeout=30)
    except (
        GoogleAPIError,
        GoogleAuthError,
        RequestException,
        RpcError,
        TimeoutError,
        MessageTooLargeError,
    ) as error:
        logger.log(logging.ERROR, FAILURE_MESSAGE, type(error).__name__)
        return ""
