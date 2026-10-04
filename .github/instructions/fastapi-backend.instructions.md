---
name: "FastAPI Backend"
description: "Use when adding or changing FastAPI routes, request/response models, CORS, file uploads, or error handlers in the HotSpot Sentinels backend. Covers async orchestration, upload validation, and status code mapping."
applyTo:
  ["backend/main.py", "backend/routers/**/*.py", "backend/models/**/*.py"]
---

# FastAPI Rules

## Route design

- All handlers are `async def`. Prefix API routes with `/api`.
- Handlers orchestrate only: validate input, call `services/` and `tools/`, shape the response. Business logic and SDK calls belong in the service modules.
- Wrap synchronous service helpers in `asyncio.to_thread` so the event loop is never blocked.
- Declare `response_model` with Pydantic v2 models mirroring the Heat Analysis Result Schema in [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md). Do not return bare dicts.

## Upload validation

Validate at the boundary, before touching any cloud service:

- Reject content types outside `image/png`, `image/jpeg`, `image/webp` with **415**.
- Enforce a `MAX_UPLOAD_BYTES` ceiling (10 MB) and return **413** when exceeded — check the read size, not just a client-supplied header.
- Constrain `ambient_temp` to a plausible range and fall back to `climate_service.get_latest_temperature()` when it is missing or implausible.

## CORS

Read allowed origins from `ALLOWED_ORIGINS` (comma-separated), defaulting to `http://localhost:8501`. Never combine `allow_origins=["*"]` with `allow_credentials=True`.

## Errors

Map service exceptions in dedicated handlers and keep responses opaque:

| Exception             | Status                  |
| --------------------- | ----------------------- |
| `VisionAnalysisError` | 502                     |
| `DatabaseError`       | 503                     |
| Validation failures   | 4xx via `HTTPException` |

Log the cause server-side; never return stack traces, SDK error payloads, project IDs, or resource paths to the client.

## Runtime

Load `.env` with `python-dotenv` at import. Bind to `PORT` (default 8080) in the `__main__` guard so local runs and Cloud Run behave identically.
