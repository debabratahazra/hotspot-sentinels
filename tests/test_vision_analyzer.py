import asyncio
import inspect
import json
import logging
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services import vision_analyzer


@pytest.fixture
def model_payload():
    return {
        "zone_id": "model-zone",
        "zone_name": "Model zone",
        "coordinates": {"lat": 1.3, "lng": 103.8},
        "ambient_temp_c": 36.5,
        "hvi_score": 8.0,
        "risk_level": "LOW",
        "surface_breakdown": {
            "asphalt_pct": 42, "dark_roof_pct": 31,
            "concrete_pct": 21, "green_canopy_pct": 7,
        },
        "passive_cooling_plan": {
            "corridor_orientation": "NE-SW",
            "retroreflective_coating_sqm": 1500.0,
            "micro_canopy_interventions": ["Plant shade trees"],
            "projected_surface_temp_drop_c": 4.0,
        },
        "alert_dispatched": True,
        "timestamp": "2026-10-02T00:00:00+00:00",
    }


@pytest.fixture
def fake_genai(monkeypatch, model_payload):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(model_payload)
    )
    monkeypatch.setattr(vision_analyzer, "get_client", lambda: client)
    return client


def test_analyze_urban_hotspot_is_async():
    assert inspect.iscoroutinefunction(vision_analyzer.analyze_urban_hotspot)


@pytest.mark.parametrize("score,expected", [
    (3.9, "LOW"), (4.0, "MODERATE"), (5.9, "MODERATE"),
    (6.0, "HIGH"), (7.9, "HIGH"), (8.0, "CRITICAL"),
])
def test_risk_level_is_derived_at_every_band_boundary(fake_genai, model_payload, score, expected):
    model_payload.update(hvi_score=score, risk_level="MODEL_SUPPLIED_WRONG_LABEL")
    fake_genai.models.generate_content.return_value.text = json.dumps(model_payload)
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 36.5))
    assert report["risk_level"] == expected


def test_returned_coordinates_are_independent_of_caller_mutation(fake_genai):
    coordinates = {"lat": 1.3, "lng": 103.8}
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(
        b"test-image", 36.5, coordinates=coordinates
    ))
    coordinates["lat"] = 999.0
    assert report["coordinates"] == {"lat": 1.3, "lng": 103.8}


def test_analyze_returns_schema_valid_report(fake_genai, sample_png_bytes):
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(sample_png_bytes, 36.5))
    validator = Path(__file__).resolve().parents[1] / ".github/skills/heat-report-validation/scripts/validate_report.py"
    result = subprocess.run(
        [sys.executable, str(validator), "-"], input=json.dumps(report),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert report["alert_dispatched"] is False


@pytest.mark.parametrize("values", [(42, 31, 21, 7), (25, 25, 25, 25), (1, 1, 1, 0)])
def test_surface_breakdown_is_integer_and_totals_exactly_100(fake_genai, model_payload, values):
    model_payload["surface_breakdown"] = dict(zip(model_payload["surface_breakdown"], values))
    fake_genai.models.generate_content.return_value.text = json.dumps(model_payload)
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 36.5))
    assert all(type(value) is int for value in report["surface_breakdown"].values())
    assert sum(report["surface_breakdown"].values()) == 100


def test_caller_zone_metadata_passes_through_verbatim(fake_genai):
    metadata = {"zone_id": " caller-zone ", "zone_name": " Caller zone ",
                "coordinates": {"lat": 1.3521, "lng": 103.8198}}
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 37.0, **metadata))
    for key, value in metadata.items():
        assert report[key] == value
    assert report["ambient_temp_c"] == 37.0


@pytest.mark.parametrize("metadata,expected_identity,expected_source", [
    ({"zone_id": " caller-zone ", "zone_name": " Caller zone ",
      "coordinates": {"lat": -90.0, "lng": 180.0}},
     {"zone_id": " caller-zone ", "zone_name": " Caller zone ",
      "coordinates": {"lat": -90.0, "lng": 180.0}},
     {"zone_id": "supplied", "zone_name": "supplied",
      "coordinates": {"lat": "supplied", "lng": "supplied"}}),
    ({}, {"zone_id": "model-zone", "zone_name": "Model zone",
          "coordinates": {"lat": 1.3, "lng": 103.8}},
     {"zone_id": "inferred", "zone_name": "inferred",
      "coordinates": {"lat": "inferred", "lng": "inferred"}}),
    ({"zone_id": " caller-zone ", "coordinates": {"lat": 12.5}},
     {"zone_id": " caller-zone ", "zone_name": "Model zone",
      "coordinates": {"lat": 12.5, "lng": 103.8}},
     {"zone_id": "supplied", "zone_name": "inferred",
      "coordinates": {"lat": "supplied", "lng": "inferred"}}),
    ({"zone_name": " Caller zone ", "coordinates": {"lng": -12.5}},
     {"zone_id": "model-zone", "zone_name": " Caller zone ",
      "coordinates": {"lat": 1.3, "lng": -12.5}},
     {"zone_id": "inferred", "zone_name": "supplied",
      "coordinates": {"lat": "inferred", "lng": "supplied"}}),
], ids=["all-supplied", "all-inferred", "mixed-lat", "mixed-lng"])
def test_identity_source_tracks_each_field_and_preserves_caller_over_model(
    fake_genai, sample_png_bytes, metadata, expected_identity, expected_source,
):
    report = asyncio.run(vision_analyzer.analyze_urban_hotspot(
        sample_png_bytes, 36.5, mime_type="image/png", **metadata,
    ))
    for field, expected in expected_identity.items():
        assert report[field] == expected
    assert report["identity_source"] == expected_source
    fake_genai.models.generate_content.assert_called_once()


def test_supplied_invalid_coordinate_still_raises_vision_analysis_error(fake_genai):
    with pytest.raises(vision_analyzer.VisionAnalysisError, match="response validation"):
        asyncio.run(vision_analyzer.analyze_urban_hotspot(
            b"test-image", 36.5, coordinates={"lat": 999.0},
        ))


@pytest.mark.parametrize("use_defaults", [False, True])
def test_model_project_and_region_are_environment_driven(monkeypatch, model_payload, use_defaults):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "offline-test-project")
    if not use_defaults:
        monkeypatch.setenv("GOOGLE_CLOUD_REGION", "qa-region")
        monkeypatch.setenv("MODEL_ID", "qa-model")
    monkeypatch.setattr(vision_analyzer, "_client", None)
    client = MagicMock()
    client.models.generate_content.return_value.text = json.dumps(model_payload)
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(vision_analyzer.genai, "Client", constructor)
    asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 36.5))
    assert vision_analyzer.get_client() is client
    constructor.assert_called_once()
    arguments = constructor.call_args.kwargs
    assert arguments["vertexai"] is True
    assert arguments["project"] == "offline-test-project"
    assert arguments["location"] == ("asia-southeast1" if use_defaults else "qa-region")
    assert client.models.generate_content.call_args.kwargs["model"] == (
        "gemini-2.5-flash" if use_defaults else "qa-model"
    )


@pytest.mark.parametrize("failure", ["sdk", "json"])
def test_sdk_and_parse_failures_raise_sanitized_vision_analysis_error(fake_genai, caplog, failure):
    raw_payload = "RAW_CLOUD_PAYLOAD projects/private-project Bearer ya29.fake-token"
    if failure == "sdk":
        fake_genai.models.generate_content.side_effect = RuntimeError(raw_payload)
    else:
        fake_genai.models.generate_content.return_value.text = raw_payload
    with caplog.at_level(logging.ERROR), pytest.raises(vision_analyzer.VisionAnalysisError) as error:
        asyncio.run(vision_analyzer.analyze_urban_hotspot(b"PRIVATE_IMAGE_BYTES", 36.5))
    combined = str(error.value) + caplog.text
    for sensitive in (raw_payload, "private-project", "ya29.fake-token", "PRIVATE_IMAGE_BYTES"):
        assert sensitive not in combined
    assert "Heat analysis failed during" in str(error.value)
    assert caplog.records
    assert all(not record.exc_info for record in caplog.records)


@pytest.mark.parametrize("invalid", ["zero_surfaces", "fractional_surface", "empty_intervention", "hvi_range"])
def test_invalid_model_fields_raise_vision_analysis_error(fake_genai, model_payload, invalid):
    if invalid == "zero_surfaces":
        model_payload["surface_breakdown"] = dict.fromkeys(model_payload["surface_breakdown"], 0)
    elif invalid == "fractional_surface":
        model_payload["surface_breakdown"]["asphalt_pct"] = 42.5
    elif invalid == "empty_intervention":
        model_payload["passive_cooling_plan"]["micro_canopy_interventions"] = [""]
    else:
        model_payload["hvi_score"] = 10.1
    fake_genai.models.generate_content.return_value.text = json.dumps(model_payload)
    with pytest.raises(vision_analyzer.VisionAnalysisError):
        asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 36.5))


def test_missing_project_raises_sanitized_configuration_error(monkeypatch):
    monkeypatch.setattr(vision_analyzer, "_client", None)
    with pytest.raises(vision_analyzer.VisionAnalysisError, match="configuration"):
        asyncio.run(vision_analyzer.analyze_urban_hotspot(b"test-image", 36.5))


def test_import_does_not_construct_genai_client():
    namespace = runpy.run_path(vision_analyzer.__file__)
    assert namespace["_client"] is None