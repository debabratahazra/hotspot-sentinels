import asyncio
import logging
import os
from threading import Lock
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from services import alert_dispatcher, database, vision_analyzer
from tools import climate_service
from tools.climate_service import get_latest_temperature
from services.vision_analyzer import HotspotAnalysisResult, IdentitySource, VisionAnalysisError, analyze_urban_hotspot
from services.database import DatabaseError, save_hotspot_report, get_recent_reports
from services.alert_dispatcher import dispatch_heat_alert
from tools.maps_imagery_service import (
    MapsImageryError,
    fetch_satellite_imagery,
    get_cached_satellite_imagery,
)

# Sprint 2 ruling: 10 MB means 10,000,000 bytes unless overridden by the environment.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "10000000"))
ALLOWED_UPLOAD_CONTENT_TYPES = {"image/jpeg", "image/png"}
READINESS_TIMEOUT_SECONDS = 5.0
READINESS_RPC_TIMEOUT_SECONDS = READINESS_TIMEOUT_SECONDS - 0.5
DEPENDENCIES = ("gemini", "firestore", "pubsub", "bigquery")
_probe_locks = {name: Lock() for name in DEPENDENCIES}


class AnalysisResponse(HotspotAnalysisResult):
    """Canonical analysis plus application-owned provenance and storage metadata.

    alert_attempted is null/absent for legacy scans, false for non-critical scans,
    and true when the critical-alert dispatcher was invoked, even if it failed.
    alert_dispatched alone records successful publication.
    """

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    climate_source: Literal["bigquery", "fallback", "caller"] | None = None
    identity_source: IdentitySource | None = None
    image_source: Literal["caller", "google_maps"] | None = None
    attribution_required: bool | None = None
    alert_attempted: bool | None = None
    doc_id: str | None = Field(default=None, min_length=1)


class ErrorResponse(BaseModel):
    code: str
    message: str


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, message=message).model_dump(),
    )


class ScanHistoryResponse(BaseModel):
    """Newest-first saved reports; an empty collection is {\"scans\": []}.

    Entries are intentionally untyped: Firestore holds records written by older schema
    versions, and one malformed historical row must not fail the whole history request.
    """

    scans: list[dict]


class HealthResponse(BaseModel):
    status: Literal["operational", "degraded"]
    dependencies: dict[str, Literal["ready", "unavailable"]]
    region: str


class LivenessResponse(BaseModel):
    status: Literal["alive"]


def check_dependency(name: str) -> str:
    """Read-only permission/connectivity probes, never inference or publication.

    Reuse lazy service clients. A still-running timed-out probe holds its lock,
    preventing repeated polling from accumulating more calls for that dependency.
    Metadata/read permissions cannot guarantee subsequent write/publish success.
    """
    lock = _probe_locks[name]
    if not lock.acquire(blocking=False):
        return "unavailable"
    try:
        timeout = READINESS_RPC_TIMEOUT_SECONDS
        if name == "gemini":
            vision_analyzer.get_client().models.get(
                model=os.getenv("MODEL_ID", "gemini-2.5-flash"),
                config={"http_options": {"timeout": int(timeout * 1000)}},
            )
        elif name == "firestore":
            database.get_db().collection(database.COLLECTION_NAME).limit(1).get(
                timeout=timeout, retry=None
            )
        elif name == "pubsub":
            publisher = alert_dispatcher._get_client()
            publisher.get_topic(
                request={"topic": publisher.topic_path(
                    alert_dispatcher.PROJECT_ID, alert_dispatcher.TOPIC_ID
                )},
                timeout=timeout,
                retry=None,
            )
        elif name == "bigquery":
            climate_service._get_client().query(
                "SELECT max FROM `bigquery-public-data.noaa_gsod.gsod*` "
                "WHERE _TABLE_SUFFIX = @table_year LIMIT 0",
                job_config=climate_service.bigquery.QueryJobConfig(
                    dry_run=True,
                    query_parameters=[climate_service.bigquery.ScalarQueryParameter(
                        "table_year", "STRING", climate_service.GSOD_YEAR
                    )],
                ),
                timeout=timeout,
                retry=None,
                job_retry=None,
            )
        else:
            raise ValueError("Unknown dependency")
        return "ready"
    except Exception as error:
        logger.warning("Readiness probe failed for %s (%s)", name, type(error).__name__)
        return "unavailable"
    finally:
        lock.release()


async def dependency_readiness(name: str) -> str:
    """Reserve half a second of the total budget for scheduling and response work."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(check_dependency, name), timeout=READINESS_RPC_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return "unavailable"

logger = logging.getLogger(__name__)
app = FastAPI(title="HotSpot Sentinels API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

def trigger_alert_if_critical(report: dict):
    report["alert_dispatched"] = False
    report["alert_attempted"] = False
    if report.get("risk_level") == "CRITICAL":
        report["alert_attempted"] = True
        report["alert_dispatched"] = bool(dispatch_heat_alert(report))

@app.exception_handler(VisionAnalysisError)
async def handle_vision_error(_request: Request, error: VisionAnalysisError):
    logger.error("Vision analysis failed (%s)", type(error).__name__)
    return error_response(502, "analysis_unavailable", "Heat analysis is unavailable.")

@app.exception_handler(DatabaseError)
async def handle_database_error(_request: Request, error: DatabaseError):
    logger.error("Scan storage failed (%s)", type(error).__name__)
    return error_response(503, "storage_unavailable", "Scan storage is unavailable.")


@app.exception_handler(MapsImageryError)
async def handle_maps_imagery_error(_request: Request, error: MapsImageryError):
    logger.error("Satellite imagery fetch failed (%s)", type(error).__name__)
    return error_response(502, "imagery_unavailable", "Satellite imagery is unavailable.")


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_request: Request, error: StarletteHTTPException):
    errors = {
        413: ("upload_too_large", "Image upload is too large."),
        415: ("unsupported_image", "Upload a JPEG or PNG image with matching content type."),
        422: ("invalid_request", "Request parameters are missing or invalid."),
        404: ("not_found", "The requested endpoint was not found."),
        405: ("method_not_allowed", "This request method is not allowed."),
    }
    code, message = errors.get(error.status_code, ("request_failed", "The request could not be completed."))
    return error_response(error.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _error: RequestValidationError):
    return error_response(422, "invalid_request", "Request parameters are missing or invalid.")


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, error: Exception):
    logger.error("Request failed (%s)", type(error).__name__)
    return error_response(500, "internal_error", "The request could not be completed. Please try again.")

@app.get("/api/live", response_model=LivenessResponse)
async def liveness_check():
    """Process liveness; use this, not dependency readiness, for restart probes."""
    return {"status": "alive"}


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Readiness details within five seconds; degradation remains HTTP 200.

    Consumers must inspect status rather than use this as a restart probe.
    BigQuery and Pub/Sub outages degrade telemetry/alerts, not process liveness.
    """
    states = await asyncio.gather(
        dependency_readiness("gemini"),
        dependency_readiness("firestore"),
        dependency_readiness("pubsub"),
        dependency_readiness("bigquery"),
    )
    return {
        "status": "operational" if all(state == "ready" for state in states) else "degraded",
        "dependencies": dict(zip(DEPENDENCIES, states)),
        "region": os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1"),
    }

@app.get(
    "/api/scans", response_model=ScanHistoryResponse, response_model_exclude_unset=True,
    responses={503: {"description": "Scan storage is unavailable."}},
)
async def get_scans(limit: int = 10):
    """Return up to limit reports, newest first. Out-of-range limits are clamped, not rejected."""
    return {"scans": await asyncio.to_thread(get_recent_reports, limit)}


@app.get("/api/imagery", responses={502: {"description": "Satellite imagery is unavailable."}})
async def get_satellite_imagery(
    lat: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
    lng: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
):
    """Serve only imagery already cached by analysis; cache misses never spend Maps quota."""
    imagery = await asyncio.to_thread(get_cached_satellite_imagery, lat, lng)
    return Response(
        content=imagery["image_bytes"],
        media_type=imagery["mime_type"],
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _validate_analysis_form(form) -> None:
    for field_name in ("zone_id", "zone_name", "lat", "lng", "imagery_lat", "imagery_lng"):
        if field_name in form and not str(form[field_name]).strip():
            raise HTTPException(status_code=422, detail="Supplied identity and imagery fields must not be blank.")


async def _read_validated_upload(file: UploadFile) -> tuple[bytes, str]:
    mime_type = file.content_type
    try:
        if mime_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported image content type.")
        image_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(image_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image upload is too large.")
        signature = b"\xff\xd8\xff" if mime_type == "image/jpeg" else b"\x89PNG\r\n\x1a\n"
        if not image_bytes.startswith(signature):
            raise HTTPException(status_code=415, detail="Unsupported image content.")
        return image_bytes, mime_type
    finally:
        await file.close()


async def _resolve_analysis_image(
    file: UploadFile | None,
    imagery_lat: float | None,
    imagery_lng: float | None,
    lat: float | None,
    lng: float | None,
) -> tuple[bytes, str, Literal["caller", "google_maps"], bool, dict[str, float] | None]:
    has_imagery_coordinate = imagery_lat is not None or imagery_lng is not None
    if file is not None and has_imagery_coordinate:
        raise HTTPException(status_code=422, detail="Supply either an image upload or imagery coordinates, not both.")
    if file is None:
        if imagery_lat is None or imagery_lng is None:
            raise HTTPException(status_code=422, detail="Supply an image upload or a complete imagery coordinate pair.")
        if lat is not None or lng is not None:
            raise HTTPException(status_code=422, detail="Use imagery_lat and imagery_lng for coordinate analysis.")
        imagery = await asyncio.to_thread(fetch_satellite_imagery, imagery_lat, imagery_lng)
        return (
            imagery["image_bytes"], imagery["mime_type"], "google_maps",
            imagery["attribution_required"], imagery["coordinate"],
        )

    image_bytes, mime_type = await _read_validated_upload(file)
    coordinates = {
        key: value for key, value in {"lat": lat, "lng": lng}.items()
        if value is not None
    } or None
    return image_bytes, mime_type, "caller", False, coordinates


@app.post("/api/analyze", response_model=AnalysisResponse, response_model_exclude_unset=True)
async def analyze_hotspot(
    request: Request,
    file: UploadFile | None = File(default=None),
    ambient_temp_c: Annotated[
        float | None, Form(ge=-50, le=60, allow_inf_nan=False)
    ] = None,
    zone_id: Annotated[str | None, Form(min_length=1)] = None,
    zone_name: Annotated[str | None, Form(min_length=1)] = None,
    lat: Annotated[
        float | None, Form(ge=-90, le=90, allow_inf_nan=False)
    ] = None,
    lng: Annotated[
        float | None, Form(ge=-180, le=180, allow_inf_nan=False)
    ] = None,
    imagery_lat: Annotated[
        float | None, Form(ge=-90, le=90, allow_inf_nan=False)
    ] = None,
    imagery_lng: Annotated[
        float | None, Form(ge=-180, le=180, allow_inf_nan=False)
    ] = None,
):
    _validate_analysis_form(await request.form())
    image_bytes, mime_type, image_source, attribution_required, coordinates = await _resolve_analysis_image(
        file, imagery_lat, imagery_lng, lat, lng
    )
    
    if ambient_temp_c is None:
        reading = await asyncio.to_thread(get_latest_temperature)
        ambient_temp = reading["max_temp_c"]
        climate_source = reading["source"]
    else:
        ambient_temp = ambient_temp_c
        climate_source = "caller"
    
    # 2. Run multimodal AI inference
    analysis_report = await analyze_urban_hotspot(
        image_bytes=image_bytes, 
        ambient_temp=ambient_temp, 
        zone_id=zone_id,
        zone_name=zone_name,
        coordinates=coordinates,
        mime_type=mime_type,
    )
    analysis_report["climate_source"] = climate_source
    analysis_report["image_source"] = image_source
    analysis_report["attribution_required"] = attribution_required
    
    # 3. Resolve alert provenance before persistence
    await asyncio.to_thread(trigger_alert_if_critical, analysis_report)
    
    # 4. Persist the final report to Firestore
    doc_id = await asyncio.to_thread(save_hotspot_report, analysis_report)
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise DatabaseError("Storage did not return a document identifier.")
    analysis_report["doc_id"] = doc_id
    
    return analysis_report
