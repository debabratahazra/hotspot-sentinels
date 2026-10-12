"""Curated public alert mirror (STORY-045).

The point of this collection is that it is world-readable, so the tests below are
mostly about what must NOT reach it.
"""

import importlib
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

database = importlib.import_module("services.database")

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "firestore.rules"

CRITICAL_REPORT = {
    "zone_id": "demo-001",
    "zone_name": "Industrial District",
    "hvi_score": 8.1,
    "risk_level": "CRITICAL",
    "ambient_temp_c": 31.0,
    "coordinates": {"lat": 1.2897, "lng": 103.754},
    "surface_breakdown": {"asphalt_pct": 55, "dark_roof_pct": 30, "concrete_pct": 10, "green_canopy_pct": 5},
    "passive_cooling_plan": {"corridor_orientation": "NE-SW", "retroreflective_coating_sqm": 4200,
                             "micro_canopy_interventions": ["shade corridors"], "projected_surface_temp_drop_c": 6.8},
    "alert_dispatched": True,
    "doc_id": "private-document-id",
    "timestamp": "2026-10-12T12:00:00Z",
}


@pytest.fixture
def captured(monkeypatch):
    """Capture what would be written, without touching Firestore."""
    written = {}
    doc = MagicMock()
    doc.id = "public-doc-1"
    doc.set.side_effect = lambda payload: written.update(payload)
    collection = MagicMock()
    collection.document.return_value = doc
    client = MagicMock()
    client.collection.return_value = collection
    monkeypatch.setattr(database, "_get_client", lambda: client)
    return written, client


def test_alerts_are_written_to_their_own_collection(captured):
    _, client = captured
    database.publish_public_alert(CRITICAL_REPORT)
    # Writing elsewhere is what keeps the scan write identifiable to the rest of
    # the suite, and keeps hotspot_scans out of the world-readable collection.
    client.collection.assert_called_once_with(database.PUBLIC_ALERTS_COLLECTION)
    assert database.PUBLIC_ALERTS_COLLECTION != database.COLLECTION_NAME


def test_critical_report_is_published_with_only_curated_fields(captured):
    written, client = captured
    assert database.publish_public_alert(CRITICAL_REPORT) == "public-doc-1"
    client.collection.assert_called_with(database.PUBLIC_ALERTS_COLLECTION)
    assert set(written) <= set(database.PUBLIC_ALERT_FIELDS) | {"detected_at"}


@pytest.mark.parametrize("field", ["passive_cooling_plan", "surface_breakdown", "doc_id", "alert_dispatched"])
def test_private_fields_never_reach_the_public_collection(captured, field):
    written, _ = captured
    database.publish_public_alert(CRITICAL_REPORT)
    assert field not in written, f"{field} must not be world-readable"


@pytest.mark.parametrize("risk", ["HIGH", "MODERATE", "LOW", "", "critical-ish"])
def test_only_critical_zones_are_published(captured, risk):
    written, client = captured
    assert database.publish_public_alert({**CRITICAL_REPORT, "risk_level": risk}) == ""
    client.collection.assert_not_called()
    assert written == {}


def test_lowercase_critical_is_still_published(captured):
    _, client = captured
    assert database.publish_public_alert({**CRITICAL_REPORT, "risk_level": "critical"})
    client.collection.assert_called_with(database.PUBLIC_ALERTS_COLLECTION)


def test_publish_failure_is_swallowed_so_analysis_still_succeeds(monkeypatch):
    def exploding():
        raise database.DatabaseError("Firestore is down")

    monkeypatch.setattr(database, "_get_client", exploding)
    # No exception: the wall is secondary to returning the caller's analysis.
    assert database.publish_public_alert(CRITICAL_REPORT) == ""


def test_rules_expose_only_the_public_collection():
    rules = RULES.read_text(encoding="utf-8")
    assert re.search(r"match /public_alerts/\{[^}]+\}\s*\{\s*allow read: if true;", rules), (
        "public_alerts must be readable for the wall to work"
    )
    assert "allow write: if false;" in rules, "clients must never write alerts"
    assert re.search(r"match /\{document=\*\*\}\s*\{\s*allow read, write: if false;", rules), (
        "everything else must default to deny, so hotspot_scans stays private"
    )
    # Comments are allowed to mention the private collection; rules are not.
    directives = re.sub(r"//.*", "", rules)
    assert "hotspot_scans" not in directives, "no rule should ever grant access to the private collection"


def test_main_publishes_after_persisting():
    source = (ROOT / "backend/main.py").read_text(encoding="utf-8")
    assert "publish_public_alert" in source, "the analysis flow must mirror critical zones"
    save_at = source.index("save_hotspot_report, analysis_report")
    publish_at = source.index("publish_public_alert, analysis_report")
    # Publishing afterwards keeps a public-mirror failure from blocking persistence.
    assert save_at < publish_at


def test_published_fields_match_the_documented_curated_set(captured):
    written, _ = captured
    database.publish_public_alert(CRITICAL_REPORT)
    # The publish body lists fields literally so the cross-layer contract check can
    # verify them; this keeps that list and PUBLIC_ALERT_FIELDS from drifting apart.
    assert set(written) - {"detected_at"} == set(database.PUBLIC_ALERT_FIELDS)
