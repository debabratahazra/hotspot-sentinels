---
name: pipeline-smoke-test
description: "Run the HotSpot Sentinels stack end to end locally and prove it works: environment check, Vertex AI connectivity, sample imagery, FastAPI startup, /api/health, /api/analyze, /api/scans, upload rejection, and Heat Analysis Result contract validation. Use when verifying a story is really done, checking nothing regressed before a deploy or demo, or confirming the whole pipeline still runs after a change."
argument-hint: "full | api-only | contract-only"
---

# Pipeline Smoke Test

Proves the stack works as a system, not as eight modules that import cleanly. Run it before every deploy, before every demo, and at the end of every sprint.

## Run it

```bash
bash .github/skills/pipeline-smoke-test/scripts/smoke_test.sh
```

The [script](./scripts/smoke_test.sh) is fail-fast and self-cleaning — it kills the API server on exit even when a step fails. Override the port with `PORT=8090`.

Steps, in order:

| #   | Step                | Fails when                                                                  |
| --- | ------------------- | --------------------------------------------------------------------------- |
| 1   | Environment doctor  | `.env` incomplete, wrong region or model, missing deps or auth              |
| 2   | `verify_setup.py`   | Vertex AI unreachable                                                       |
| 3   | Sample imagery      | `data_samples/` empty and `seed_samples.py` fails                           |
| 4   | API startup         | uvicorn dies, or `/api/health` never answers within 30s                     |
| 5   | Routes              | analyze or scans returns non-2xx, or a text upload is not rejected with 415 |
| 6   | Contract validation | the payload breaks the Heat Analysis Result schema or HVI rules             |

## When a step fails

Diagnose at the failing layer — do not restart from step 1.

| Step | First thing to check                                                                       |
| ---- | ------------------------------------------------------------------------------------------ |
| 1    | Run the `gcp-environment-doctor` skill; it prints the exact fix                            |
| 2    | Region must be `asia-southeast1`, model `gemini-2.5-flash`                                 |
| 3    | `GCS_BUCKET_NAME` set; the seeder must still write local files when upload fails           |
| 4    | Read the printed API log — an import-time crash in a service module is the usual cause     |
| 5    | 415 missing means upload validation was never implemented; 502 means `VisionAnalysisError` |
| 6    | Use the `heat-report-validation` skill to find which layer drifted                         |

The script prints the API log path and the captured payload path on failure. Read them before theorising.

## Prerequisites

`.env` must exist (`./setup_gcp.sh`), dependencies installed (`pip install -r requirements.txt`), and `backend/main.py` must exist. Before Story 4.1 lands there is no API to test — run the `gcp-environment-doctor` skill instead.

## Constraints

- DO NOT modify production code to make the smoke test pass. File a bug and fix it as a story.
- DO NOT skip step 6. A 200 response that breaks the schema is a failure, not a pass.
- This test writes real Firestore documents and may publish real Pub/Sub messages. That is intentional — it is an integration test, not a unit test. Keep it out of CI unless CI has credentials.
