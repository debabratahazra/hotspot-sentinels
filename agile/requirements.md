# HotSpot Sentinels Requirements

## Product goal

Enable urban analysts and city planners to identify heat-island hotspots from aerial imagery and ambient temperature telemetry, assess heat vulnerability, obtain passive cooling recommendations, review stored scans, and trigger critical-heat events through an evaluable Google Cloud AI Builder Cup sustainability submission. ([G], §1; [E9], Goal)

## Functional requirements

1. **FR-1 — Provision cloud environment:** Provision the required Vertex AI, Cloud Run, Storage, BigQuery, Pub/Sub and Firestore APIs and resources idempotently and write the core environment variables to `.env`. ([E1], Story 1.1)
2. **FR-2 — Verify Vertex AI connectivity:** The connectivity check shall print a Gemini reply on success and exit non-zero on failure using environment-selected project, region and model values. ([E1], Story 1.2)
3. **FR-3 — Analyse aerial imagery:** Produce a Heat Analysis Result from an aerial image and ambient temperature with the guide's zone identity, coordinates, temperature, HVI, risk, surface breakdown, cooling plan, dispatch state and UTC timestamp fields, including integer surface percentages summing to 100, preserving validated caller-supplied `zone_id`, `zone_name`, `lat` and `lng` verbatim without model override and using best-effort Gemini inference only for omitted identity fields. ([G], §3; [E2], Goal and Story 2.1; resolved OQ-1, 2026-10-02)
4. **FR-4 — Score heat vulnerability:** Assign an HVI score from 1.0 to 10.0 such that the industrial asphalt preset scores higher than the green park preset. ([B], Story 1.1; [E2], Story 2.3)
5. **FR-5 — Derive risk level:** Derive `risk_level` from HVI as LOW below 4.0, MODERATE from 4.0 to below 6.0, HIGH from 6.0 to below 8.0, and CRITICAL at or above 8.0, rather than accepting an independent model classification. ([G], HVI Risk Bands; [E2], Story 2.1)
6. **FR-6 — Recommend passive cooling:** Return a cooling plan containing wind-corridor orientation, retroreflective coating area, micro-canopy interventions and projected surface-temperature reduction. ([G], §3; [B], Story 1.1)
7. **FR-7 — Seed synthetic imagery:** Generate industrial asphalt, mixed residential and green park RGB presets locally and upload them under `samples/` in the configured GCS bucket when available, retaining local files on upload failure. ([B], Story 1.2; [E2], Story 2.2)
8. **FR-8 — Retrieve climate telemetry:** Retrieve the most recent valid NOAA GSOD 2024 station reading from BigQuery with station ID, observation date, maximum and average Celsius temperatures, and `source=bigquery`, excluding missing-value sentinels. ([B], Story 2.1; [E3], Story 3.1)
9. **FR-9 — Fall back on unavailable telemetry:** Return `source=fallback` with a maximum temperature of 35–41 °C and an average approximately 5–7 °C lower when cloud telemetry fails or has no valid rows. ([E3], Story 3.2)
10. **FR-10 — Publish critical alerts:** Publish a JSON Pub/Sub event only for HVI at or above 8.0 containing zone identity, coordinates, ambient temperature, HVI, risk, urgent interventions and dispatch time, without failing the analysis if publishing fails. ([G], HVI Risk Bands; [E4], Story 4.2)
11. **FR-11 — Report actual alert provenance:** Set the returned and stored `alert_dispatched` flag from successful Pub/Sub publication, keeping it false on publish failure or HVI below 8.0. ([E4], Story 4.3)
12. **FR-12 — Persist scan reports:** Save the complete scan report and cooling plan to Firestore's `hotspot_scans` collection and return its generated document ID, reporting storage failure rather than claiming success. ([G], §2; [E4], Story 4.1 and Failure policy)
13. **FR-13 — Retrieve recent reports:** Retrieve Firestore reports newest first with a requested limit clamped to 1–100 and JSON-serialisable timestamps. ([E4], Story 4.1)
14. **FR-14 — Expose service readiness:** `GET /api/health` shall return HTTP 200 with independent cloud-dependency readiness, project and region, including a degraded status when a dependency is unavailable. ([E5], Story 5.1)
15. **FR-15 — Expose analysis API:** `POST /api/analyze` shall accept an image, ambient temperature and optional multipart `zone_id`, `zone_name`, `lat` and `lng` fields, reject supplied empty identity strings or coordinates outside the inclusive latitude -90..90 and longitude -180..180 ranges with HTTP 422, and return a validated unified report with `doc_id` and `climate_source` that preserves supplied identity values verbatim and uses best-effort Gemini inference for omitted fields and telemetry when temperature is absent or implausible. ([E5], Endpoints and Story 5.2; resolved OQ-1, 2026-10-02)
16. **FR-16 — Reject unsafe uploads:** Reject uploads outside PNG, JPEG and WebP with HTTP 415 and uploads exceeding the specified 10 MB byte limit with HTTP 413 before any cloud call. ([E5], Story 5.3)
17. **FR-17 — Expose safe service errors:** Return generic HTTP 502 responses for vision-analysis failures and HTTP 503 responses for database failures without exposing stack traces or resource paths. ([E5], Story 5.4)
18. **FR-18 — Expose scan history API:** `GET /api/scans` shall return recent scans newest first and HTTP 200 with an empty list when no scans exist. ([E5], Story 5.5)
19. **FR-19 — Build backend container:** Build a reproducible multi-stage backend image from the repository root that starts the API on the configured port. ([B], Story 4.2; [E6], Story 6.1)
20. **FR-20 — Deploy backend to Cloud Run:** Deploy a git-SHA-tagged backend image through Artifact Registry to a Cloud Run HTTPS service with runtime environment configuration and a reported service URL, revision and image digest. ([E6], Goal and Stories 6.2–6.4)
21. **FR-21 — Verify and roll back deployment:** Verify deployed health and schema-valid analysis responses and restore a previous revision by shifting traffic rather than deleting the service. ([E6], Story 6.4)
22. **FR-22 — Render heat-analysis dashboard:** Provide a dark Streamlit dashboard with Singapore/Bangkok/Delhi selection, a 30–45 °C simulation slider, preset or uploaded imagery, API-triggered analysis, an image and HVI badge, telemetry provenance, cooling blueprint, recent scans and a critical banner reflecting actual dispatch state. ([B], Story 5.1; [E7], Stories 7.1–7.4)
23. **FR-23 — Render degraded dashboard states:** Keep the dashboard readable with loading indicators and generic error or missing-data states for slow, unavailable, failed or incomplete API responses and missing presets. ([E7], Story 7.5)
24. **FR-24 — Prove behaviour offline:** Provide an offline pytest suite covering acceptance criteria, service success and failure paths, API status codes, HVI boundaries and valid and invalid report contracts without credentials or cloud calls. ([E8], Goal and Stories 8.1–8.4)
25. **FR-25 — Report test coverage:** Produce a per-sprint report of total and per-file coverage and its change from the previous sprint, identifying touched files below the 70% floor for test-task follow-up. ([E8], Story 8.5)
26. **FR-26 — Document setup and architecture:** Provide a README with runnable setup commands, the problem and sustainability approach, stack, deployed URL and epic catalogue, plus a diagram matching the actual telemetry, analysis, persistence and critical-alert flow. ([E9], Stories 9.1–9.2)
27. **FR-27 — Rehearse a repeatable demo:** Provide and rehearse a timed low-risk and critical-risk demo runbook with pre-flight checks, reset steps and network, quota and cold-start fallbacks. ([E9], Story 9.3)
28. **FR-28 — Deliver competition submission:** Submit the required shared repository, reachable deployed URL, uploaded demo recording and completed competition forms before the deadline with a clean contract audit and latest sprint report. ([E9], Story 9.4)
29. **FR-29 — Expose zone identity provenance:** Identify each report's `zone_id`, `zone_name`, `lat` and `lng` individually as caller-supplied or model-inferred so a consumer can distinguish authoritative input from best-effort inference. ([G], §3; resolved OQ-1, 2026-10-02)
30. **FR-30 — Document client analysis inputs:** Provide one external API consumer guide explaining how to choose `zone_id`, source `zone_name` and read `lat`/`lng` from a map source for the imagery, accepted image formats and size limit, metric-unit expectations, the supplied-versus-inferred identity rule and a worked multipart `curl` example. ([E9], Story 9.1; resolved OQ-1, 2026-10-02)
31. **FR-31 — Retain scan imagery:** Persist uploaded aerial crops and generated heatmaps to `GCS_BUCKET_NAME` under deterministic object prefixes with their stored object URIs in the persisted scan record, logging storage failures safely and continuing analysis without claiming successful object storage. ([G], §2; resolved OQ-3, 2026-10-02; NFR-5, NFR-7 and NFR-14)
32. **FR-32 — Analyse Maps imagery by coordinate:** Accept a valid latitude and longitude instead of an uploaded file, fetch satellite imagery from the Maps Static API on the backend, and analyse it through the existing heat-report flow while continuing to accept uploads. ([G], §3; resolved OQ-6, 2026-10-03)
33. **FR-33 — Report image-source provenance:** Include `image_source` in each new analysis response and stored scan with `caller` for an uploaded image or `google_maps` for imagery fetched for the requested coordinate. ([G], §3; resolved OQ-6, 2026-10-03)

## Non-functional requirements

1. **NFR-1 — Singapore region:** Use `asia-southeast1` for all configurable Google Cloud service locations. One narrow exception: a BigQuery job must run in the location of the data it reads, and `bigquery-public-data.noaa_gsod` is US multi-region, so `climate_service.py` uses `BIGQUERY_LOCATION` (default `US`) for that public-dataset read only. Every resource this project owns stays in `asia-southeast1`. ([G], §2; [C], Hard constraints)
2. **NFR-2 — Metric units:** Use only °C, m, m² and km² in system inputs and outputs, converting source measurements before they reach the UI. ([G], §2–3; [C], Hard constraints)
3. **NFR-3 — Modern GenAI SDK:** Use only `google.genai` through `from google import genai`, never `vertexai.generative_models` or `google.generativeai`. ([G], §2; [C], Hard constraints)
4. **NFR-4 — Configured Gemini model:** Use `gemini-2.5-flash` on Vertex AI through `MODEL_ID`. ([G], §2; [C], Hard constraints)
5. **NFR-5 — Environment-driven configuration:** Read project, region, bucket, topic, model, origins, port and API base URL from environment configuration with documented defaults and no hardcoded project, bucket, topic or deployed-URL literals. ([C], Environment; [E1], Environment contract; [E7], Story 7.1)
6. **NFR-6 — Keyless authentication:** Use Application Default Credentials and the Cloud Run runtime identity without creating service-account key files or committing `.env` or credentials. ([C], Conventions; [E1], Story 1.4; [E6], Story 6.3)
7. **NFR-7 — Safe logs and responses:** Never log secrets, credentials, image bytes or raw cloud error payloads, and keep client error messages generic. ([C], Conventions; [E5], Story 5.4)
8. **NFR-8 — One-way layering:** Keep `main.py` as the sole HTTP orchestrator, prohibit `services/` and `tools/` from importing `main` or each other, and restrict the dashboard to API presentation without HVI computation, unit conversion or direct cloud access. ([C], Architecture; [E5], Scope; [E7], Scope)
9. **NFR-9 — Coverage floor:** Maintain total test coverage at or above 70% and flag each touched file below 70% for test-task follow-up. ([E8], Story 8.5 and Definition of done)
10. **NFR-10 — Async API runtime:** Use FastAPI async routes served on Cloud Run port 8080 by default, wrapping synchronous cloud helpers in `asyncio.to_thread` so they do not block the event loop. ([C], Hard constraints and Conventions; [E5], Story 5.2)
11. **NFR-11 — Supported Python:** Run the backend on Python 3.10 or newer. ([G], §2; [C], Hard constraints)
12. **NFR-12 — Restricted container identity:** Run the credential-free container as a non-root user with a dedicated runtime service account holding only the five capability roles specified in EPIC-06, never Owner or Editor. ([E6], Stories 6.1–6.3)
13. **NFR-13 — Safe request boundaries:** Parameterise station queries, configure CORS from `ALLOWED_ORIGINS` without wildcard origins paired with credentials, and apply explicit timeouts to readiness checks and dashboard requests. ([E3], Story 3.1; [E5], Stories 5.1 and 5.4; [E7], Story 7.5)
14. **NFR-14 — Controlled cloud boundaries:** Lazily construct and cache module-level cloud clients and translate SDK failures at service boundaries rather than leaking raw exceptions to callers. ([C], Conventions; [E4], Failure policy)
15. **NFR-15 — Keep the Maps API key secret:** Keep `GOOGLE_MAPS_API_KEY` on the backend and never expose it to the browser, logs, logged request URLs or client-facing errors. ([R], 2026-10-03)
16. **NFR-16 — Preserve Maps attribution and conserve quota:** Keep Google's imagery attribution watermark visible and serve an identical normalized imagery request from cache without another Maps API fetch. ([R], 2026-10-03)

## Out of scope

- Weather forecasting, historical climate trend analysis and additional telemetry data sources. ([E3], Scope)
- Pub/Sub subscribers or delivery through notification channels such as email or SMS. ([E4], Scope)
- Live cloud calls in the automated QA suite; live integration remains a separate manual pre-deploy or pre-demo check. ([E8], Scope)
- New product features added solely for the demo or submission. ([E9], Scope)

## Open questions

- **OQ-2 — Validation limits:** What exact temperature range counts as plausible for API input, and does the documented 10 MB upload limit mean 10,000,000 or 10,485,760 bytes? ([E5], Stories 5.2–5.3)
- **OQ-5 — Performance and cost limits:** What numeric readiness/request timeout limits and cloud-spend ceiling should acceptance use, given that sources call for short or explicit timeouts and avoiding unnecessary cloud spend but specify no values? ([E5], Stories 5.1 and 5.3; [E7], Story 7.5)

These questions require human answers for the affected items before they can be groomed as ready; no unspecified values or additional scope are assumed here.

Source reconciliation: the guide's 4.0/6.0/8.0 band boundaries and inclusive critical threshold govern FR-5 and FR-10 despite older `> 8.0` wording in [B]; EPIC-04's explicit publication-failure policy governs FR-11, so a critical score alone never proves dispatch success.

## Resolved questions

- **OQ-1 — Zone identity and coordinates (resolved 2026-10-02):** The caller may supply any of `zone_id`, `zone_name`, `lat` and `lng` as multipart form fields alongside the image; the backend validates supplied non-empty identity strings and inclusive latitude -90..90 and longitude -180..180 ranges, returning HTTP 422 for invalid input, and passes valid supplied values into the report verbatim without model override, while Gemini infers each omitted field from the image on a best-effort basis and the report exposes each field's supplied or inferred provenance; an external-client guide explains identity and map-coordinate sourcing, image formats and size limits, metric units and a worked `curl` request (FR-3, FR-15, FR-29 and FR-30). Rationale: accept both identity mechanisms while keeping caller input authoritative and inference distinguishable. ([G], §3; [E5], Story 5.2; human decision, 2026-10-02)
- **OQ-3 — GCS heatmap scope (resolved 2026-10-02):** Object storage extends beyond synthetic samples to uploaded aerial crops and generated heatmaps in `GCS_BUCKET_NAME`, using deterministic prefixes and persisting stored object URIs on scan records, with safe logging and continued analysis on storage failure (FR-31). EPIC-005 owns this upload-to-persisted-scan workflow rather than EPIC-002's analysis and sample-generation scope; no new heatmap-generation workflow is implied. Rationale: retain the artifacts underlying a scan while preserving the existing graceful-degradation policy, environment-driven bucket configuration and safe logging boundaries. ([G], §2; NFR-5, NFR-7 and NFR-14; human decision, 2026-10-02)
- **OQ-4 — Competition constraints (resolved 2026-10-04):** The submission deadline is one week out, 2026-10-11. The demo recording is capped at **3 minutes**, which is a hard editorial constraint on Story 9.3 rather than a target. Repository sharing is satisfied by a GitHub repository or any Google-provided repository, so no hosting migration is required. The deployed GCP stack is the artefact under demonstration: submission readiness is proven by deploying the current codebase to Cloud Run and verifying it end to end, not by a separate demo build. Rationale: a 3-minute ceiling forces the demo to show one coordinate-to-report path rather than a feature tour, and anchoring the demo to the deployed revision keeps the recording and the judged system identical. ([R], human decision, 2026-10-04)
- **OQ-6 — Location input and Maps failure policy (resolved 2026-10-03):** The analyst supplies raw `lat` and `lng`; existing city presets remain convenient coordinate shortcuts, and place-name geocoding is out of scope. Maps imagery is fetched only when no file is uploaded and a complete valid coordinate pair is supplied; an uploaded file remains authoritative and keeps the existing optional coordinate identity fields. A Maps fetch failure returns a generic HTTP 502 for that coordinate request, while the upload path remains available and unaffected. The report records image origin as `image_source=caller` or `image_source=google_maps`. Rationale: raw coordinates enable analysis anywhere without introducing an unrequested geocoder, preserve the existing upload contract, and avoid mistaking an unavailable source for valid analysis. ([R], 2026-10-03)
- **OQ-7 — Maps attribution and quota policy (resolved 2026-10-03):** Preserve the returned Google attribution watermark without cropping and cache successful imagery by normalized request parameters so identical requests do not cause another Maps API fetch. Rationale: attribution is a terms requirement and request reuse directly conserves the limited API quota. ([R], 2026-10-03)

## Traceability

The IDs and titles below are those returned by `python3 .github/skills/agile-sdlc-loop/scripts/backlog.py list --type epic`; document labels EPIC-01 through EPIC-09 correspond to backlog IDs EPIC-001 through EPIC-009. EPIC-010 is the new backlog epic in this change.

| Requirement | Delivering epic ID |
| ----------- | ------------------ |
| FR-1        | EPIC-001           |
| FR-2        | EPIC-001           |
| FR-3        | EPIC-002           |
| FR-4        | EPIC-002           |
| FR-5        | EPIC-002           |
| FR-6        | EPIC-002           |
| FR-7        | EPIC-002           |
| FR-8        | EPIC-003           |
| FR-9        | EPIC-003           |
| FR-10       | EPIC-004           |
| FR-11       | EPIC-004           |
| FR-12       | EPIC-004           |
| FR-13       | EPIC-004           |
| FR-14       | EPIC-005           |
| FR-15       | EPIC-005           |
| FR-16       | EPIC-005           |
| FR-17       | EPIC-005           |
| FR-18       | EPIC-005           |
| FR-19       | EPIC-006           |
| FR-20       | EPIC-006           |
| FR-21       | EPIC-006           |
| FR-22       | EPIC-007           |
| FR-23       | EPIC-007           |
| FR-24       | EPIC-008           |
| FR-25       | EPIC-008           |
| FR-26       | EPIC-009           |
| FR-27       | EPIC-009           |
| FR-28       | EPIC-009           |
| FR-29       | EPIC-002           |
| FR-30       | EPIC-009           |
| FR-31       | EPIC-005           |
| FR-32       | EPIC-010           |
| FR-33       | EPIC-010           |

| Epic ID  | Exact backlog title                         | Source document |
| -------- | ------------------------------------------- | --------------- |
| EPIC-001 | Foundation and Environment                  | [E1]            |
| EPIC-002 | Multimodal Perception and Gemini Reasoning  | [E2]            |
| EPIC-003 | Climate Telemetry and Ingestion             | [E3]            |
| EPIC-004 | Event-Driven Resilience Pipeline            | [E4]            |
| EPIC-005 | FastAPI Core Service and Agentic Controller | [E5]            |
| EPIC-006 | Containerization and Cloud Run Deployment   | [E6]            |
| EPIC-007 | Interactive Dashboard and Heat Visualizer   | [E7]            |
| EPIC-008 | Quality Assurance and Test Coverage         | [E8]            |
| EPIC-009 | Demo, Documentation and Submission          | [E9]            |
| EPIC-010 | Coordinate-Based Maps Imagery               | [R]             |

**Coverage:** 33/33 functional requirements map to exactly one epic; 10/10 epics receive at least one functional requirement; no FR or epic is uncovered. The 16 non-functional requirements apply across their cited scopes. OQ-1, OQ-3, OQ-4, OQ-6 and OQ-7 are resolved; OQ-2 and OQ-5 remain unresolved decisions for their affected items, so the full Phase 0 exit remains conditional on those answers.

[G]: ../COPILOT_GUIDE.md
[B]: ../Epics_Stories.md
[C]: ../.github/copilot-instructions.md
[E1]: ../.github/docs/epics/EPIC-01-foundation-environment.md
[E2]: ../.github/docs/epics/EPIC-02-multimodal-perception.md
[E3]: ../.github/docs/epics/EPIC-03-climate-telemetry.md
[E4]: ../.github/docs/epics/EPIC-04-resilience-pipeline.md
[E5]: ../.github/docs/epics/EPIC-05-api-service.md
[E6]: ../.github/docs/epics/EPIC-06-containerization-deployment.md
[E7]: ../.github/docs/epics/EPIC-07-dashboard.md
[E8]: ../.github/docs/epics/EPIC-08-quality-assurance.md
[E9]: ../.github/docs/epics/EPIC-09-demo-submission.md
[R]: Human requirement and verified Maps Static API behavior, 2026-10-03
