# EPIC-05 — FastAPI Core Service & Agentic Controller

|                |                                                                                                                                         |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | One HTTP surface that orchestrates perception, telemetry, persistence, and alerting, and returns a single unified Heat Analysis Result. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 4, Story 4.1                                                                         |
| **Priority**   | P1                                                                                                                                      |
| **Status**     | Not started                                                                                                                             |
| **Depends on** | EPIC-02, EPIC-03, EPIC-04                                                                                                               |
| **Delivers**   | `backend/main.py`                                                                                                                       |

## Why this epic exists

This is the only layer allowed to know the whole story. The services deliberately know nothing about each other — `main.py` is where they are composed into a single request. It is also the project's trust boundary: every untrusted byte arrives here.

## Scope

**In:** route definitions, request validation, response models, CORS, error mapping, orchestration.

**Out:** business logic. A route that computes an HVI score or converts a unit is a bug — that belongs in a service module.

## Endpoints

| Method | Path                  | Returns                                                         |
| ------ | --------------------- | --------------------------------------------------------------- |
| GET    | `/api/health`         | Readiness of each cloud dependency, project, region             |
| POST   | `/api/analyze`        | Unified Heat Analysis Result plus `doc_id` and `climate_source` |
| GET    | `/api/scans?limit=10` | Recent scans, newest first                                      |

## Stories

### Story 5.1 — Health endpoint
- **File:** `backend/main.py`
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Reports readiness of the genai client, Firestore, Pub/Sub, and BigQuery independently
  - [ ] Returns project and region, never credentials or full client config
  - [ ] Returns 200 with a degraded body rather than 500 when one dependency is down — a liveness probe should not flap
  - [ ] No cloud call takes longer than a short timeout

### Story 5.2 — Analyze endpoint
- **File:** `backend/main.py`
- **Estimate:** 5 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Accepts `image: UploadFile`, `ambient_temp: float = Form(...)`, optional `zone_name`
  - [ ] Falls back to `climate_service.get_latest_temperature()` when `ambient_temp` is absent or implausible, and reports which was used via `climate_source`
  - [ ] Calls `vision_analyzer.analyze_urban_hotspot`, then `database.save_hotspot_report`, then `alert_dispatcher.dispatch_heat_alert`
  - [ ] Sets `alert_dispatched` from the returned message ID
  - [ ] Returns a `response_model`-validated payload, not a bare dict
  - [ ] Synchronous service helpers wrapped in `asyncio.to_thread`
  - [ ] Response passes `validate_report.py`

### Story 5.3 — Upload validation and limits
- **File:** `backend/main.py`
- **Estimate:** 2 · **Priority:** P0 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Content types outside `image/png`, `image/jpeg`, `image/webp` rejected with **415**
  - [ ] Bodies over `MAX_UPLOAD_BYTES` (10 MB) rejected with **413**, measured on bytes actually read rather than a client-supplied header
  - [ ] `ambient_temp` constrained to a plausible range
  - [ ] `limit` on `/api/scans` clamped before it reaches Firestore
  - [ ] Validation happens before any cloud call, so a bad request costs nothing

### Story 5.4 — CORS and error mapping
- **File:** `backend/main.py`
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Origins read from `ALLOWED_ORIGINS`, defaulting to `http://localhost:8501`
  - [ ] `allow_origins=["*"]` is never paired with `allow_credentials=True`
  - [ ] `VisionAnalysisError` → 502, `DatabaseError` → 503 via exception handlers
  - [ ] Client responses are generic; stack traces, SDK payloads, project IDs, and resource paths stay in server logs
  - [ ] `.env` loaded at import; uvicorn binds `PORT` (default 8080) in the `__main__` guard

### Story 5.5 — Scans endpoint
- **File:** `backend/main.py`
- **Estimate:** 1 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Returns recent scans from `database.get_recent_reports(limit)`
  - [ ] Empty collection returns `[]` with 200, not an error
  - [ ] Every field is JSON-serialisable

## Definition of done

`uvicorn main:app --port 8080` serves all three routes, the `pipeline-smoke-test` skill passes end to end including the 415 negative case, and EPIC-08 covers each status code with mocked services.

## Risks

| Risk                                          | Mitigation                                                                          |
| --------------------------------------------- | ----------------------------------------------------------------------------------- |
| Blocking cloud calls freezing the event loop  | `asyncio.to_thread`; the `contract-auditor` agent flags direct calls in `async def` |
| Oversized or malicious uploads                | Story 5.3, enforced before any cloud spend                                          |
| Error responses leaking infrastructure detail | Generic messages; audited every sprint                                              |
| Wildcard CORS with credentials                | The `enforce-hard-constraints` hook blocks that edit                                |
| Business logic creeping into routes           | Layering rule audited each sprint                                                   |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "FastAPI Core Service and Agentic Controller" --priority P1 \
  --description "HTTP surface orchestrating perception, telemetry, persistence and alerting"
bl add --type story --parent EPIC-005 --priority P1 --estimate 2 --source requirements \
  --title "As an operator I can check whether the service and its dependencies are ready" \
  --files backend/main.py \
  --ac "reports each cloud dependency independently" "never returns credentials" "200 with a degraded body when one dependency is down"
bl add --type story --parent EPIC-005 --priority P1 --estimate 5 --source requirements \
  --title "As an analyst I can upload an aerial image and receive a full heat report" \
  --files backend/main.py \
  --ac "returns a schema-valid Heat Analysis Result" "persists the scan and returns doc_id" \
       "alert_dispatched reflects the real Pub/Sub outcome" "climate_source names the temperature provenance"
bl add --type story --parent EPIC-005 --priority P0 --estimate 2 --source requirements \
  --title "As an operator the API rejects unsafe uploads before spending cloud budget" \
  --files backend/main.py \
  --ac "415 on non-image content type" "413 above 10 MB" "validation precedes any cloud call"
bl add --type story --parent EPIC-005 --priority P1 --estimate 2 --source requirements \
  --title "As a frontend developer I get usable errors without leaked internals" \
  --files backend/main.py \
  --ac "VisionAnalysisError maps to 502" "DatabaseError maps to 503" \
       "no stack traces or resource paths in responses" "CORS origins from ALLOWED_ORIGINS"
bl add --type story --parent EPIC-005 --priority P2 --estimate 1 --source requirements \
  --title "As an analyst I can list recent scans" \
  --files backend/main.py \
  --ac "returns newest first" "empty collection returns an empty list with 200"
```
