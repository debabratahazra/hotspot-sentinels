# EPIC-02 — Multimodal Perception & Gemini Reasoning

|                |                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Goal**       | Turn an aerial image plus an ambient temperature into a contract-valid Heat Analysis Result: surface breakdown, HVI score, and a passive cooling plan. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 1; [COPILOT_GUIDE.md](../../../COPILOT_GUIDE.md) §3                                                 |
| **Priority**   | P1                                                                                                                                                     |
| **Status**     | In progress                                                                                                                                            |
| **Depends on** | EPIC-01                                                                                                                                                |
| **Delivers**   | `backend/services/vision_analyzer.py`, `backend/tools/seed_samples.py`                                                                                 |

## Why this epic exists

This is the product. Everything downstream — Firestore, Pub/Sub, the API, the dashboard — moves the output of this epic around. If the schema here is wrong, every other layer is wrong with it.

## Scope

**In:** the Gemini call, the system instruction and scoring rubric, structured JSON output, the error type, and the synthetic imagery used to exercise it.

**Out:** persistence, alerting, HTTP. The analyzer returns a dict and raises on failure; it decides nothing about what happens next.

## Stories

### Story 2.1 — Vision inference module
- **File:** `backend/services/vision_analyzer.py`
- **Estimate:** 5 · **Priority:** P1 · **Status:** In progress
- **Source:** original Story 1.1
- **Acceptance criteria:**
  - [x] Uses `from google import genai` with `genai.Client(vertexai=True, ...)`
  - [x] Forces structured output via `response_mime_type="application/json"` and a `response_schema`
  - [x] System instruction carries the urban-climatologist persona and the HVI rubric
  - [ ] Signature is `async def analyze_urban_hotspot(image_bytes: bytes, ambient_temp: float, zone_name: str) -> dict`
  - [ ] Returned dict matches the Heat Analysis Result schema exactly
  - [ ] `risk_level` is derived from `hvi_score` in code, not trusted from the model
  - [ ] `surface_breakdown` percentages are integers summing to 100
  - [ ] Model id from `MODEL_ID`, project from `GOOGLE_CLOUD_PROJECT`, region from `GOOGLE_CLOUD_REGION`
  - [ ] Mime type derived from the caller's upload, not hardcoded to JPEG
  - [ ] Blocking SDK call wrapped in `asyncio.to_thread`
  - [ ] Client built lazily once and cached at module level
  - [ ] Raises `VisionAnalysisError` on SDK failure or unparseable output
  - [ ] Never logs image bytes or credentials

**Known gaps in the current implementation** — all are schema or constraint violations, not style:

| Gap                                                                         | Impact                                                           |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Function is synchronous                                                     | Blocks the FastAPI event loop in EPIC-05                         |
| Schema is missing `zone_id`, `coordinates`, `alert_dispatched`, `timestamp` | Firestore documents and API responses will be incomplete         |
| Has `requires_emergency_alert` instead of `alert_dispatched`                | EPIC-04's dispatcher and the dashboard both read the wrong field |
| Has extra `surface_temp_estimate_c` not in the contract                     | Undocumented field; either add it to the guide or drop it        |
| `surface_breakdown` fields are `float`                                      | Contract requires integers summing to 100                        |
| Model id, region, and mime type hardcoded                                   | Breaks the env-driven config rule                                |
| `os.popen("gcloud config get-value project")` at import                     | Shells out on every import; fails in a container                 |
| New `genai.Client` per call                                                 | Wasteful; client should be cached                                |
| No error type                                                               | SDK exceptions leak across the service boundary                  |

Validate any fix with the `heat-report-validation` skill before calling this story done.

### Story 2.2 — Synthetic aerial imagery seeder
- **File:** `backend/tools/seed_samples.py`
- **Estimate:** 2 · **Priority:** P2 · **Status:** In progress
- **Source:** original Story 1.2
- **Acceptance criteria:**
  - [x] Generates distinguishable RGB scenes with Pillow — no external assets
  - [ ] Produces **three** scenes: high-density industrial asphalt, mixed residential with canopy, green open park
  - [ ] Lives in `backend/tools/` so it sits beside `climate_service.py`
  - [ ] Uploads to `GCS_BUCKET_NAME` under a `samples/` prefix
  - [ ] Still succeeds offline — warns and keeps local files when the bucket is unset or upload fails
  - [ ] Writes paths relative to the repository root, not the current working directory
- **Known gaps:** only two images exist (`industrial_hotspot.jpg`, `cool_park.jpg`); the mixed-residential scene is missing. There is no GCS upload at all — `GCS_BUCKET_NAME` is never read. `os.makedirs("data_samples")` resolves against the caller's cwd, so running it from `backend/` writes to the wrong place.

### Story 2.3 — Scoring rubric hardening
- **File:** `backend/services/vision_analyzer.py`
- **Estimate:** 2 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] The two preset extremes score in the expected direction — industrial asphalt materially higher HVI than green park
  - [ ] Percentages are normalised after parsing when the model returns a near-100 total
  - [ ] Band boundaries 4.0 / 6.0 / 8.0 exist as one shared constant, not repeated literals
  - [ ] A malformed or truncated model response raises `VisionAnalysisError` rather than returning a partial dict

## Definition of done

`analyze_urban_hotspot` is async, returns a payload that passes `validate_report.py`, is covered by mocked unit tests from EPIC-08, and the seeder produces three scenes locally and in GCS.

## Risks

| Risk                                                       | Mitigation                                                                                            |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Schema drift between this module and the API, store and UI | Run the `contract-auditor` agent every sprint; `heat-report-validation` is the single source of truth |
| Model returns prose instead of JSON                        | `response_schema` plus a hard parse failure, never a silent fallback                                  |
| Percentages do not total 100                               | Normalise defensively after parsing; assert it in tests                                               |
| Quota or region errors mistaken for code bugs              | Run the `gcp-environment-doctor` skill first                                                          |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Multimodal Perception and Gemini Reasoning" --priority P1 \
  --description "Aerial image plus ambient temperature to a contract-valid Heat Analysis Result"
bl add --type story --parent EPIC-002 --priority P1 --estimate 5 --source requirements \
  --title "As an analyst I can score a zone from an aerial image" \
  --files backend/services/vision_analyzer.py \
  --ac "analyze_urban_hotspot is async" \
       "returned payload passes validate_report.py" \
       "risk_level derived from hvi_score in code" \
       "model, project and region read from env vars" \
       "VisionAnalysisError raised on SDK or parse failure"
bl add --type story --parent EPIC-002 --priority P2 --estimate 2 --source requirements \
  --title "As a developer I have three synthetic aerial scenes to test against" \
  --files backend/tools/seed_samples.py \
  --ac "three distinguishable scenes written to data_samples/" \
       "uploaded to GCS_BUCKET_NAME under samples/" \
       "succeeds offline with a warning"
bl add --type story --parent EPIC-002 --priority P2 --estimate 2 --source requirements \
  --title "As an analyst I can trust the HVI rubric to rank zones consistently" \
  --files backend/services/vision_analyzer.py \
  --ac "industrial scene scores materially higher than park scene" \
       "surface percentages normalised to 100" \
       "band boundaries defined once"
```
