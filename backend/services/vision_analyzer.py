import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)
_client: genai.Client | None = None
RISK_BANDS = ((4.0, "LOW"), (6.0, "MODERATE"), (8.0, "HIGH"))

SYSTEM_INSTRUCTION = (
    "You are an expert urban climatologist and satellite analyst. "
    "Analyze aerial imagery with the reported ambient temperature in Celsius. "
    "Use this fixed planning rubric, not a measured surface temperature or a "
    "clinically validated health-risk index. First estimate surface_breakdown "
    "as integer percentages totaling 100 using only asphalt_pct, dark_roof_pct, "
    "concrete_pct and green_canopy_pct. Use visible tree canopy, not all green "
    "pixels, for green_canopy_pct; do not mistake ponds for dark impervious "
    "surfaces. Use these same percentages in the score, not a second material "
    "classification. Compute five dimensionless components from 0 to 1: "
    "absorption = (asphalt_pct + dark_roof_pct + 0.5 * concrete_pct) / 100 "
    "(45% weight: dark impervious surfaces absorb more heat than light concrete); "
    "canopy_deficit = 1 - green_canopy_pct / 100 "
    "(25% weight: canopy provides shade and evaporative cooling); "
    "shade_deficit = 1 - the fraction of non-canopy ground visibly shaded by "
    "buildings or shade structures (10% weight: exposed ground heats more; "
    "exclude tree shade already represented by canopy; use 0 when no "
    "non-canopy ground exists); built_density = the fraction of the whole image "
    "occupied by building roof footprints, including light roofs "
    "(10% weight: dense buildings retain heat and constrain ventilation); "
    "ambient_heat = (reported ambient_temp_c - 20) / 20, clipped to 0 through 1 "
    "(10% weight: 20 Celsius or cooler contributes zero, 40 Celsius or hotter "
    "contributes fully, with linear interpolation between). Estimate shade "
    "and density fractions to the nearest 0.1 from visible evidence; if either "
    "cannot be resolved, use 0.5 for that component consistently. Calculate "
    "hvi_score = 1 + 9 * (0.45 * absorption + 0.25 * canopy_deficit + "
    "0.10 * shade_deficit + 0.10 * built_density + 0.10 * ambient_heat). "
    "Round only the final score to one decimal place; do not add discretionary "
    "adjustments or use zone names as evidence. The range is 1.0 to 10.0. "
    "Calibration at a shared ambient temperature of 35 Celsius: LOW resembles "
    "cool_park.jpg, dense canopy with a pond and light paths; MODERATE resembles "
    "mixed_residential.jpg, a road grid with medium roofs, driveways, lawns and "
    "scattered canopy; HIGH resembles a mostly impervious, densely built zone "
    "with sparse canopy and some structural shade; CRITICAL resembles "
    "industrial_hotspot.jpg, mostly asphalt and dark roofs, little shade and "
    "only a token green patch. At identical ambient temperature the intended "
    "calibration order is industrial_hotspot.jpg strictly above "
    "mixed_residential.jpg strictly above cool_park.jpg; derive the scores from "
    "the rubric rather than assigning scores from filenames or forcing bands. "
    "Recommend passive, "
    "non-mechanical cooling; name a compass axis for ventilation corridors and "
    "justify it with prevailing monsoon winds. All temperatures are Celsius "
    "and all areas are square metres. Infer zone_id, zone_name and coordinates "
    "only when not supplied; infer each missing coordinate component independently. "
    "Never override supplied metadata. Return only the "
    "structured Heat Analysis Result. Set alert_dispatched to false; the service "
    "generates the final UTC timestamp and derives the final risk level."
)


class VisionAnalysisError(Exception):
    """Heat analysis could not produce a valid report."""


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class CoordinateIdentitySource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    lat: Literal["supplied", "inferred"]
    lng: Literal["supplied", "inferred"]


class IdentitySource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    zone_id: Literal["supplied", "inferred"]
    zone_name: Literal["supplied", "inferred"]
    coordinates: CoordinateIdentitySource


class SurfaceBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    asphalt_pct: int = Field(ge=0, le=100)
    dark_roof_pct: int = Field(ge=0, le=100)
    concrete_pct: int = Field(ge=0, le=100)
    green_canopy_pct: int = Field(ge=0, le=100)


class PassiveCoolingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    corridor_orientation: str = Field(min_length=3)
    retroreflective_coating_sqm: float = Field(ge=0)
    micro_canopy_interventions: list[str] = Field(min_length=1)
    projected_surface_temp_drop_c: float = Field(ge=0, le=20)


class HotspotAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    zone_id: str = Field(min_length=1)
    zone_name: str = Field(min_length=1)
    coordinates: Coordinates
    ambient_temp_c: float = Field(ge=-50, le=60)
    hvi_score: float = Field(ge=1, le=10)
    risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    surface_breakdown: SurfaceBreakdown
    passive_cooling_plan: PassiveCoolingPlan
    alert_dispatched: bool
    timestamp: str


def get_client() -> genai.Client:
    global _client
    if _client is None:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project or not project.strip():
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set for heat analysis")
        _client = genai.Client(
            vertexai=True,
            project=project,
            location=os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1"),
        )
    return _client


def risk_level_for_score(hvi_score: float) -> str:
    for ceiling, label in RISK_BANDS:
        if hvi_score < ceiling:
            return label
    return "CRITICAL"


def _normalize_surfaces(surface: SurfaceBreakdown) -> dict[str, int]:
    values = surface.model_dump()
    total = sum(values.values())
    if total == 0:
        raise ValueError("Surface percentages must have a positive total")
    normalized = {key: value * 100 // total for key, value in values.items()}
    remainder = 100 - sum(normalized.values())
    ranked = sorted(values, key=lambda key: values[key] * 100 % total, reverse=True)
    for key in ranked[:remainder]:
        normalized[key] += 1
    return normalized


async def analyze_urban_hotspot(
    image_bytes: bytes,
    ambient_temp: float,
    zone_name: str | None = None,
    *,
    mime_type: str = "image/jpeg",
    zone_id: str | None = None,
    coordinates: dict[str, float] | None = None,
) -> dict:
    """Return a contract-valid report without publishing or persisting it."""
    stage = "configuration (GOOGLE_CLOUD_PROJECT is required)"
    try:
        metadata = {
            key: value
            for key, value in {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "coordinates": coordinates.copy() if coordinates is not None else None,
            }.items()
            if value is not None
        }
        prompt = (
            f"Reported ambient temperature: {ambient_temp} Celsius. "
            f"Caller-supplied zone metadata: {json.dumps(metadata)}. "
            "Evaluate surface materials, heat vulnerability, and passive cooling."
        )

        def generate_content():
            nonlocal stage
            client = get_client()
            stage = "model generation"
            return client.models.generate_content(
                model=os.getenv("MODEL_ID", "gemini-2.5-flash"),
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=HotspotAnalysisResult,
                    temperature=0.0,
                ),
            )

        response = await asyncio.to_thread(generate_content)
        stage = "response validation"
        payload = json.loads(response.text)
        if coordinates is not None:
            metadata["coordinates"] = {
                **payload.get("coordinates", {}), **coordinates,
            }
        payload.update(metadata)
        payload["ambient_temp_c"] = ambient_temp
        payload["risk_level"] = risk_level_for_score(payload["hvi_score"])
        # The dispatcher flips this only after a successful publish.
        payload["alert_dispatched"] = False
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        report = HotspotAnalysisResult.model_validate(payload)
        if any(not item for item in report.passive_cooling_plan.micro_canopy_interventions):
            raise ValueError("Canopy interventions must not be empty")
        result = report.model_dump()
        result["surface_breakdown"] = _normalize_surfaces(report.surface_breakdown)
        result["identity_source"] = IdentitySource(
            zone_id="supplied" if zone_id is not None else "inferred",
            zone_name="supplied" if zone_name is not None else "inferred",
            coordinates=CoordinateIdentitySource(
                lat="supplied" if coordinates is not None and "lat" in coordinates else "inferred",
                lng="supplied" if coordinates is not None and "lng" in coordinates else "inferred",
            ),
        ).model_dump()
        return result
    except Exception as exc:
        logger.exception(
            "Heat analysis failed during %s (%s)", stage, type(exc).__name__, exc_info=False
        )
        raise VisionAnalysisError(f"Heat analysis failed during {stage}.") from None
