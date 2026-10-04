import logging
import os
from datetime import datetime, timezone
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import firestore
from requests.exceptions import RequestException

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
COLLECTION_NAME = "hotspot_scans"
_CLOUD_ERRORS = (GoogleAPIError, GoogleAuthError, RequestException)
_client: firestore.Client | None = None
logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Firestore persistence or history is unavailable."""


def _get_client() -> firestore.Client:
    global _client
    if _client is None:
        try:
            _client = firestore.Client(project=PROJECT_ID)
        except (*_CLOUD_ERRORS, OSError) as error:
            logger.log(logging.ERROR, "Firestore client failed (%s)", type(error).__name__)
            raise DatabaseError("Scan storage is unavailable.") from None
    return _client


def get_db() -> firestore.Client:
    return _get_client()


def _serialize_timestamps(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {key: _serialize_timestamps(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_timestamps(item) for item in value]
    return value


def save_hotspot_report(report: dict) -> str:
    """Save a complete report without changing its analysis timestamp or input."""
    stored_report = dict(report)
    if "timestamp" not in stored_report:
        stored_report["timestamp"] = datetime.now(timezone.utc).isoformat()
        stored_report["created_at"] = firestore.SERVER_TIMESTAMP
    try:
        doc_ref = _get_client().collection(COLLECTION_NAME).document()
        doc_ref.set(stored_report)
        logger.info("Saved hotspot report to Firestore")
        return doc_ref.id
    except _CLOUD_ERRORS as error:
        logger.log(logging.ERROR, "Firestore write failed (%s)", type(error).__name__)
        raise DatabaseError("Unable to save the scan report.") from None


def get_recent_reports(limit: int = 10) -> list[dict]:
    """Return bounded, newest-first history with JSON-safe UTC timestamps."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("History limit must be an integer.")
    limit = max(1, min(limit, 100))
    try:
        docs = _get_client().collection(COLLECTION_NAME).order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        return [_serialize_timestamps(doc.to_dict()) for doc in docs]
    except _CLOUD_ERRORS as error:
        logger.log(logging.ERROR, "Firestore read failed (%s)", type(error).__name__)
        raise DatabaseError("Unable to retrieve scan history.") from None
