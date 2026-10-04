---
name: "FastAPI Controller"
description: "Scaffold backend/main.py: the FastAPI service exposing /api/health, /api/analyze, and /api/scans, wiring vision analysis, climate telemetry, Firestore, and Pub/Sub alerts."
argument-hint: "Optional: extra endpoints or response fields"
agent: "agent"
tools: ["edit", "search", "runCommands", "problems"]
---

Build the agentic API controller for HotSpot Sentinels (Epic 4 / Story 4.1).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md). All routes are `async def`.

## Target file

`backend/main.py`

## Endpoints

1. `GET /api/health` — reports readiness of each cloud dependency (GenAI client, Firestore, Pub/Sub, BigQuery) plus project and region. Never return credentials or full client config.
2. `POST /api/analyze` — multipart upload:
   - `image: UploadFile` and `ambient_temp: float = Form(...)`, optional `zone_name: str = Form("Unnamed Zone")`.
   - If `ambient_temp` is not supplied or is out of range, fall back to `climate_service.get_latest_temperature()`.
   - Call `vision_analyzer.analyze_urban_hotspot(...)`, persist via `database.save_hotspot_report(...)`, then call `alert_dispatcher.dispatch_heat_alert(...)`.
   - Set `alert_dispatched` from whether a message ID came back, and return the unified Heat Analysis Result JSON plus `doc_id` and `climate_source`.
3. `GET /api/scans?limit=10` — returns recent scans from `database.get_recent_reports(limit)`.

## Implementation rules

- Define Pydantic v2 response models mirroring the guide's schema; do not return bare dicts from route handlers.
- CORS: read allowed origins from an `ALLOWED_ORIGINS` env var (comma-separated), defaulting to `http://localhost:8501`. Do not pair `allow_origins=["*"]` with `allow_credentials=True`.
- Validate uploads at the boundary: reject content types outside `image/png`, `image/jpeg`, `image/webp` with 415, and reject bodies over a `MAX_UPLOAD_BYTES` constant (e.g. 10 MB) with 413.
- Wrap blocking service calls in `asyncio.to_thread` where the underlying helper is synchronous.
- Map `VisionAnalysisError` to 502 and `DatabaseError` to 503 via exception handlers; return generic messages to clients and log details server-side — never leak stack traces or cloud error payloads in responses.
- Load `.env` with `python-dotenv` at import; bind uvicorn to the `PORT` env var (default 8080) in the `__main__` guard.

## Done when

- `uvicorn main:app --port 8080` starts from the `backend/` directory and `GET /api/health` returns 200.
