# EPIC-01 — Foundation & Environment

|                |                                                                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | Every developer and every agent can reach Google Cloud, read configuration from one place, and import the backend packages without surprises. |
| **Source**     | [COPILOT_GUIDE.md](../../../COPILOT_GUIDE.md) §2 Hard Technical Constraints; [setup_gcp.sh](../../../setup_gcp.sh)                            |
| **Priority**   | P1                                                                                                                                            |
| **Status**     | In progress                                                                                                                                   |
| **Depends on** | —                                                                                                                                             |
| **Delivers**   | `setup_gcp.sh`, `.env`, `requirements.txt`, `.gitignore`, `backend/verify_setup.py`, package `__init__.py` files                              |

## Why this epic exists

The original backlog assumed the environment was already working. It mostly is — but the gaps here surface as confusing failures in every later epic: a hardcoded project ID, a missing `tools/` package, a `.env` that never got committed to `.gitignore`. Fix the foundation once instead of debugging it five times.

## Scope

**In:** cloud resource provisioning, credential strategy, environment variable contract, dependency baseline, repository hygiene, package layout.

**Out:** anything that calls Gemini (EPIC-02), any application code.

## Environment contract

Every module reads these and nothing else. No literals in source, ever.

| Variable               | Default                  | Used by            |
| ---------------------- | ------------------------ | ------------------ |
| `GOOGLE_CLOUD_PROJECT` | — (required)             | all cloud clients  |
| `GOOGLE_CLOUD_REGION`  | `asia-southeast1`        | genai, Cloud Run   |
| `GCS_BUCKET_NAME`      | `${PROJECT}-data`        | seeder, storage    |
| `PUBSUB_TOPIC_ID`      | `heat-resilience-alerts` | alert dispatcher   |
| `GOOGLE_MAPS_API_KEY`  | — (required)             | Maps Static API    |
| `MODEL_ID`             | `gemini-2.5-flash`       | vision analyzer    |
| `ALLOWED_ORIGINS`      | `http://localhost:8501`  | FastAPI CORS       |
| `PORT`                 | `8080`                   | uvicorn, Cloud Run |

Restrict `GOOGLE_MAPS_API_KEY` to the Maps Static API and approved referrers/IP addresses; an unrestricted key is a deployment risk.

## Stories

Each story has a detailed specification with Given/When/Then acceptance criteria and test cases in [../user-stories](../user-stories/README.md):

| Story | Detail                                                                                                  | Priority | Est | Status      |
| ----- | ------------------------------------------------------------------------------------------------------- | -------- | --- | ----------- |
| 1.1   | [US-01.1 Provision the cloud environment](../user-stories/US-01.1-gcp-provisioning-script.md)           | P1       | 2   | Done (gap)  |
| 1.2   | [US-01.2 Verify Vertex AI connectivity](../user-stories/US-01.2-vertex-ai-connectivity-check.md)        | P1       | 1   | In progress |
| 1.3   | [US-01.3 Dependency baseline](../user-stories/US-01.3-dependency-baseline.md)                           | P1       | 1   | Done        |
| 1.4   | [US-01.4 Keep credentials out of version control](../user-stories/US-01.4-repository-secret-hygiene.md) | **P0**   | 1   | In progress |
| 1.5   | [US-01.5 Backend package layout](../user-stories/US-01.5-backend-package-layout.md)                     | P1       | 1   | In progress |

### Story 1.1 — GCP provisioning script
- **File:** `setup_gcp.sh`
- **Estimate:** 2 · **Priority:** P1 · **Status:** Done
- **Acceptance criteria:**
  - [x] Enables aiplatform, run, storage, bigquery, pubsub, firestore APIs
  - [x] Creates the GCS bucket, Pub/Sub topic, and Firestore native database in `asia-southeast1` if absent, and is safe to re-run
  - [x] Writes `.env` with all five core variables
- **Known gaps:** does not emit `ALLOWED_ORIGINS`; [Epics_Stories.md](../../../Epics_Stories.md) refers to `setup_gcp.zsh`, the real filename is `setup_gcp.sh`.

### Story 1.2 — Vertex AI connectivity check
- **File:** `backend/verify_setup.py`
- **Estimate:** 1 · **Priority:** P1 · **Status:** In progress
- **Acceptance criteria:**
  - [x] Calls `gemini-2.5-flash` through `genai.Client(vertexai=True, ...)` and prints the reply
  - [ ] Reads project and region from env vars, not `os.popen("gcloud config get-value project")`
  - [ ] Exits non-zero on failure so scripts can branch on it
- **Known gaps:** shells out to `gcloud` at import and hardcodes `REGION`/`MODEL_ID`; always exits 0 even when the call fails.

### Story 1.3 — Dependency baseline
- **File:** [requirements.txt](../../../requirements.txt)
- **Estimate:** 1 · **Priority:** P1 · **Status:** Done
- **Acceptance criteria:**
  - [x] Runtime deps: google-genai, cloud clients, fastapi, uvicorn, pydantic, pillow, python-dotenv
  - [x] Frontend deps: streamlit, requests
  - [x] Test deps: pytest, pytest-cov, httpx
  - [x] A clean `pip install -r requirements.txt` into a fresh venv succeeds

### Story 1.4 — Repository and secret hygiene
- **File:** [.gitignore](../../../.gitignore)
- **Estimate:** 1 · **Priority:** P0 · **Status:** In progress
- **Acceptance criteria:**
  - [x] `.gitignore` excludes `.env`, key files, `*.pem`, `venv/`, coverage artefacts, `data_samples/`
  - [ ] The repository is initialised with git — until then `.gitignore` protects nothing
  - [ ] `git status` shows no `.env` and no credential file
- **Known gaps:** this directory is not yet a git repository. Run `git init` before `.env` exists.

### Story 1.5 — Backend package layout
- **Files:** `backend/services/__init__.py`, `backend/tools/__init__.py`
- **Estimate:** 1 · **Priority:** P1 · **Status:** In progress
- **Acceptance criteria:**
  - [x] `backend/services/` is a package
  - [ ] `backend/tools/` exists as a package — `seed_samples.py` currently sits in `backend/` root
  - [ ] `python -c "import services.vision_analyzer"` works from `backend/`, matching how uvicorn runs
- **Known gaps:** no `tools/` package, so EPIC-03's `climate_service.py` has nowhere to land.

## Definition of done

`./setup_gcp.sh` provisions cleanly from scratch, `python backend/verify_setup.py` prints a Gemini response and exits 0, `python3 .github/skills/gcp-environment-doctor/scripts/doctor.py` reports all green, and `git status` is free of secrets.

## Risks

| Risk                                              | Mitigation                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `.env` committed before `git init`                | Story 1.4 — initialise the repo now; the `guard-secrets` hook already blocks agent access to `.env` |
| Project ID drift between gcloud config and `.env` | The environment doctor checks they match                                                            |
| Region typo outside `asia-southeast1`             | The `enforce-hard-constraints` hook blocks the edit                                                 |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Foundation and Environment" --priority P1 \
  --description "GCP provisioning, env contract, dependency baseline, repo hygiene, package layout"
bl add --type task --parent EPIC-001 --priority P0 --estimate 1 --source requirements \
  --title "Initialise the git repository so .gitignore takes effect" \
  --ac "git status runs" "no .env or credential file is tracked"
bl add --type task --parent EPIC-001 --priority P1 --estimate 1 --source requirements \
  --title "Make verify_setup.py read project, region and model from env vars" \
  --files backend/verify_setup.py \
  --ac "no os.popen call at import" "exits non-zero on failure"
bl add --type task --parent EPIC-001 --priority P1 --estimate 1 --source requirements \
  --title "Create the backend/tools package" \
  --files backend/tools/__init__.py \
  --ac "backend/tools/__init__.py exists" "imports resolve when uvicorn runs from backend/"
```
