# User Stories — Index

One file per user story. Stories are grouped by their parent epic in [../epics](../epics/) and carry the epic's number as a prefix.

## EPIC-01 — Foundation & Environment

| Story                                                | Title                                                   | Priority | Est | Status |
| ---------------------------------------------------- | ------------------------------------------------------- | -------- | --- | ------ |
| [US-01.1](./US-01.1-gcp-provisioning-script.md)      | Provision the Google Cloud environment with one command | P1       | 2   | Done   |
| [US-01.2](./US-01.2-vertex-ai-connectivity-check.md) | Verify Vertex AI connectivity before building anything  | P1       | 1   | Done   |
| [US-01.3](./US-01.3-dependency-baseline.md)          | Install every dependency from one manifest              | P1       | 1   | Done   |
| [US-01.4](./US-01.4-repository-secret-hygiene.md)    | Keep credentials out of version control                 | **P0**   | 1   | Done   |
| [US-01.5](./US-01.5-backend-package-layout.md)       | Import backend modules the same way uvicorn does        | P1       | 1   | Done   |

Epic total: 6 points. All five stories are Done; sprint 1 closed 9/9 committed items and EPIC-001 is closed. The original US-01 documents are retained unchanged as the house-style baseline; this index records their current completion state.

## EPIC-02 — Multimodal Perception & Gemini Reasoning

| Story                                                                                 | Title                                           | Priority | Est | Status  |
| ------------------------------------------------------------------------------------- | ----------------------------------------------- | -------- | --- | ------- |
| [US-02.1](./US-02.1-score-a-zone-from-an-aerial-image.md) (`STORY-001`)               | Score a zone from an aerial image               | P2       | 5   | Done    |
| [US-02.2](./US-02.2-three-synthetic-aerial-scenes.md) (`STORY-002`)                   | Generate three synthetic aerial scenes          | P2       | 2   | Done    |
| [US-02.3](./US-02.3-trust-the-hvi-rubric-to-rank-zones-consistently.md) (`STORY-003`) | Trust the HVI rubric to rank zones consistently | P2       | 2   | Ready   |
| [US-02.4](./US-02.4-distinguish-supplied-and-inferred-zone-identity.md) (`STORY-030`) | Distinguish supplied and inferred zone identity | P1       | 2   | Blocked |

Epic story total: 11 points. STORY-001 and STORY-002 were delivered in sprint 1.

## EPIC-03 — Climate Telemetry & Ingestion

| Story                                                                           | Title                                             | Priority | Est | Status  |
| ------------------------------------------------------------------------------- | ------------------------------------------------- | -------- | --- | ------- |
| [US-03.1](./US-03.1-ground-score-in-real-temperature.md) (`STORY-004`)          | Ground the zone score in real ambient temperature | P1       | 3   | Blocked |
| [US-03.2](./US-03.2-keep-working-when-bigquery-is-unavailable.md) (`STORY-005`) | Keep working when BigQuery is unavailable         | P1       | 2   | Blocked |
| [BUG-010](../../../agile/backlog.json)                                          | BigQuery query interpolates station ID into SQL   | **P0**   | 1   | New     |

Epic story total: 5 points; BUG-010 is a separate existing bug, not a user-story document.

## EPIC-04 — Event-Driven Resilience Pipeline

| Story                                                                                  | Title                                                   | Priority | Est | Status  |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------- | -------- | --- | ------- |
| [US-04.1](./US-04.1-see-previous-scans.md) (`STORY-006`)                               | See previous scans                                      | P1       | 3   | Blocked |
| [US-04.2](./US-04.2-alert-automatically-when-a-zone-becomes-critical.md) (`STORY-007`) | Receive an automatic alert when a zone becomes critical | P1       | 3   | Blocked |
| [US-04.3](./US-04.3-trust-the-stored-alert-dispatch-flag.md) (`STORY-008`)             | Trust the stored alert-dispatch flag                    | P1       | 1   | Blocked |

Epic story total: 7 points.

## EPIC-05 — FastAPI Core Service & Agentic Controller

| Story                                                                                | Title                                          | Priority | Est | Status  |
| ------------------------------------------------------------------------------------ | ---------------------------------------------- | -------- | --- | ------- |
| [US-05.1](./US-05.1-check-service-readiness.md) (`STORY-009`)                        | Check service and dependency readiness         | P1       | 2   | Blocked |
| [US-05.2](./US-05.2-upload-an-image-and-receive-a-full-heat-report.md) (`STORY-010`) | Upload an image and receive a full heat report | P1       | 5   | Blocked |
| [US-05.3](./US-05.3-reject-unsafe-uploads-before-cloud-spend.md) (`STORY-011`)       | Reject unsafe uploads before cloud spend       | P1       | 2   | Blocked |
| [US-05.4](./US-05.4-receive-usable-errors-without-leaked-internals.md) (`STORY-012`) | Receive usable errors without leaked internals | P1       | 2   | Blocked |
| [US-05.5](./US-05.5-list-recent-scans.md) (`STORY-013`)                              | List recent scans                              | P1       | 1   | Blocked |
| [US-05.6](./US-05.6-supply-and-validate-zone-identity-on-upload.md) (`STORY-029`)    | Supply and validate zone identity on upload    | P1       | 3   | Blocked |
| [US-05.7](./US-05.7-retrieve-the-aerial-image-behind-a-scan.md) (`STORY-031`)        | Retrieve the aerial image behind a scan        | P2       | 3   | Blocked |
| [BUG-007](../../../agile/backlog.json)                                               | Analysis never awaits the async analyzer       | **P0**   | 2   | New     |
| [BUG-008](../../../agile/backlog.json)                                               | Critical alerts read a deleted schema field    | **P0**   | 1   | New     |
| [BUG-009](../../../agile/backlog.json)                                               | CORS ignores ALLOWED_ORIGINS                   | P1       | 1   | New     |

Epic story total: 18 points; the three bugs are separate existing backlog items.

## EPIC-06 — Containerization & Cloud Run Deployment

| Story                                                             | Title                                | Priority | Est | Status  |
| ----------------------------------------------------------------- | ------------------------------------ | -------- | --- | ------- |
| [US-06.1](./US-06.1-reproducible-backend-image.md) (`STORY-014`)  | Build a reproducible backend image   | P1       | 3   | Blocked |
| [US-06.2](./US-06.2-deploy-backend-to-cloud-run.md) (`STORY-015`) | Deploy the backend to Cloud Run      | P1       | 3   | Blocked |
| [US-06.3](./US-06.3-verify-deploy-and-roll-back.md) (`STORY-016`) | Verify a deployment and roll it back | P1       | 2   | Blocked |

Epic story total: 8 points. TASK-004 (2) and TASK-013 (1) are folded into US-06.2, separately estimated. Existing TASK-024 (EPIC-001, 1 point) tracks the duplicate dependency manifest and is referenced by US-06.1; it is not moved or duplicated.

## EPIC-07 — Interactive Dashboard & Heat Visualizer

| Story                                                             | Title                                                    | Priority | Est | Status  |
| ----------------------------------------------------------------- | -------------------------------------------------------- | -------- | --- | ------- |
| [US-07.1](./US-07.1-run-analysis-from-dashboard.md) (`STORY-017`) | Choose a city, temperature and image and run an analysis | P1       | 3   | Blocked |
| [US-07.2](./US-07.2-hvi-score-at-a-glance.md) (`STORY-018`)       | See the HVI score and risk level at a glance             | P1       | 3   | Blocked |
| [US-07.3](./US-07.3-passive-cooling-blueprint.md) (`STORY-019`)   | Read the passive cooling blueprint                       | P1       | 3   | Blocked |
| [US-07.4](./US-07.4-critical-alert-confirmation.md) (`STORY-020`) | See confirmation that a critical alert was dispatched    | P1       | 1   | Blocked |
| [US-07.5](./US-07.5-readable-degraded-dashboard.md) (`STORY-021`) | Keep the dashboard readable when something goes wrong    | P1       | 2   | Blocked |

Epic story total: 12 points. STORY-021 stays P1 as recorded in the backlog, despite the older epic document's P2. Deleted-field defects in analysis/history require orchestrator filing, separate from backend BUG-008.

## EPIC-08 — Quality Assurance & Test Coverage

| Story                                                          | Title                                        | Priority | Est | Status  |
| -------------------------------------------------------------- | -------------------------------------------- | -------- | --- | ------- |
| [US-08.1](./US-08.1-run-suite-offline.md) (`STORY-022`)        | Run the whole suite offline with one command | P1       | 3   | Blocked |
| [US-08.2](./US-08.2-mocked-service-coverage.md) (`STORY-023`)  | Prove every service with mocked unit tests   | P1       | 5   | Blocked |
| [US-08.3](./US-08.3-api-status-code-coverage.md) (`STORY-024`) | Prove every API status code                  | P1       | 3   | Blocked |
| [US-08.4](./US-08.4-payload-contract-tests.md) (`STORY-025`)   | Enforce the payload contract with tests      | P1       | 2   | Blocked |

Epic story total: 13 points. TASK-005 (2, P2) is folded into US-08.2. Baseline: 82 passing offline tests, 61.7% whole-backend coverage; the 70% NFR-9 floor is not yet met. Both legacy live-cloud scripts must be retired.

## EPIC-09 — Demo, Documentation & Submission

| Story                                                             | Title                                                | Priority | Est | Status  |
| ----------------------------------------------------------------- | ---------------------------------------------------- | -------- | --- | ------- |
| [US-09.1](./US-09.1-readme-only-project-setup.md) (`STORY-026`)   | Understand and run the project from the README alone | P1       | 2   | Blocked |
| [US-09.2](./US-09.2-system-architecture-diagram.md) (`STORY-027`) | See how the system fits together                     | P2       | 2   | Blocked |
| [US-09.3](./US-09.3-repeatable-end-to-end-demo.md) (`STORY-028`)  | Run the demo reliably end to end                     | P2       | 3   | Blocked |
| [US-09.4](./US-09.4-api-client-input-guide.md) (`STORY-032`)      | Know exactly what to send to the analysis API        | P2       | 2   | Blocked |

Epic story total: 9 points. TASK-006 (2, P2) is folded into US-09.3. Recording limit, deadline and sharing/form requirements remain **TBD (OQ-4)**; no competition values are invented.

Index statuses above reflect current backlog state, with the explicit sprint-1 completion update for EPIC-01. Ready, Blocked and New retain their backlog meanings; document headers may additionally describe implementation progress using the house vocabulary below. All priorities and estimates are preserved, and task/bug points are not added to story estimates. EPIC-02 through EPIC-05 documents are owned by the concurrent Product Owner run; this pass only indexes them.

## EPIC-10 — Coordinate-Based Maps Imagery

| Story                                                                                     | Title                                               | Priority | Est | Status |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------- | -------- | --- | ------ |
| [US-10.1](./US-10.1-fetch-attributed-satellite-imagery-for-a-coordinate.md) (`STORY-034`) | Fetch attributed satellite imagery for a coordinate | P2       | 3   | New    |
| [US-10.2](./US-10.2-analyse-a-location-without-an-upload.md) (`STORY-035`)                | Analyse a location without an upload                | P2       | 5   | New    |
| [US-10.3](./US-10.3-choose-any-location-in-the-dashboard.md) (`STORY-036`)                | Choose any location in the dashboard                | P2       | 3   | New    |
| [US-10.4](./US-10.4-protect-the-maps-key-and-conserve-imagery-quota.md) (`STORY-037`)     | Protect the Maps key and conserve imagery quota     | P2       | 5   | New    |

Epic story total: 16 points. Raw latitude/longitude is the analyst input; existing city presets remain coordinate shortcuts and place-name geocoding is out of scope (resolved OQ-6).

## Naming convention

`US-<epic>.<story>-<kebab-title>.md` — for example `US-02.1-score-zone-from-aerial-image.md`.

Keep the number stable once a story is written. If scope changes materially, cancel the story and write a new one rather than renumbering — the backlog, sprint reports, and retros all reference these IDs.

## Anatomy of a story

| Section             | Purpose                                                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Header table        | ID, epic, priority, estimate, status, owning agent, files touched                                                                    |
| User story          | The `As a … I want … so that …` statement — a user-visible outcome, never a layer                                                    |
| Acceptance criteria | Given/When/Then, each one independently checkable. These become the pytest cases in [EPIC-08](../epics/EPIC-08-quality-assurance.md) |
| Tasks               | The implementation checklist — what a developer actually does                                                                        |
| Current state       | What exists today and what is wrong with it, grounded in the real code                                                               |
| Test cases          | What QA must assert, named so the test file can copy them                                                                            |
| Definition of done  | The bar for moving to `done`                                                                                                         |

A story with no acceptance criteria is not ready for grooming. A story whose criteria cannot be observed from outside the code is not a user story — it is a task.

## Status vocabulary

| Status      | Meaning                                                                  |
| ----------- | ------------------------------------------------------------------------ |
| Not started | No code exists                                                           |
| In progress | Code exists, acceptance criteria unmet                                   |
| Done (gap)  | Primary criteria met, follow-up tasks remain and are listed in the story |
| Done        | Every criterion demonstrated and covered by a passing test               |

## Seeding the backlog

Each story file ends with a `backlog.py` command. Seeding from the [epic documents](../epics/) creates the same items in bulk — use one route or the other, not both, or you will get duplicates.
