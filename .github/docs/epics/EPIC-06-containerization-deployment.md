# EPIC-06 — Containerization & Cloud Run Deployment

|                |                                                                                                                        |
| -------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Goal**       | The backend runs as a reproducible, credential-free container on Cloud Run in `asia-southeast1`, reachable over HTTPS. |
| **Source**     | [Epics_Stories.md](../../../Epics_Stories.md) Epic 4, Story 4.2 — expanded to cover deployment, IAM, and verification  |
| **Priority**   | P1                                                                                                                     |
| **Status**     | Not started                                                                                                            |
| **Depends on** | EPIC-05                                                                                                                |
| **Delivers**   | `backend/Dockerfile`, `backend/.dockerignore`, a live Cloud Run service                                                |

## Why this epic exists

The original backlog stopped at "write a Dockerfile". A Dockerfile that is never deployed, whose service account lacks `roles/aiplatform.user`, and whose health check was never called, is not a deliverable. This epic covers everything between the image and a URL that works.

## Build context — the trap

`requirements.txt` lives at the **repository root**, so the image must be built from the root:

```bash
docker build -f backend/Dockerfile -t hotspot-sentinels .
```

A `--source ./backend` or `docker build ./backend` invocation cannot reach `requirements.txt` and fails. Every `COPY` path is written relative to the repo root.

## Stories

### Story 6.1 — Multi-stage Dockerfile
- **Files:** `backend/Dockerfile`, `backend/.dockerignore`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Multi-stage on `python:3.11-slim`: builder installs dependencies, runtime copies only packages and app source
  - [ ] `WORKDIR /app`; `requirements.txt` copied before source so the dependency layer caches
  - [ ] `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `pip install --no-cache-dir`
  - [ ] Runs as a non-root user
  - [ ] `EXPOSE 8080`; uvicorn started in exec form on `0.0.0.0`, honouring `$PORT`
  - [ ] `.dockerignore` excludes `venv/`, `.env*`, `data_samples/`, `__pycache__/`, `.git/`, `*-key.json`, `*.pem`
  - [ ] `docker build -f backend/Dockerfile -t hotspot-sentinels .` succeeds from the repo root

### Story 6.2 — Artifact Registry and deploy
- **File:** `.github/skills/cloudrun-deploy/scripts/deploy.sh`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Artifact Registry repo created in `asia-southeast1` if absent
  - [ ] Image tagged with the short git SHA, not only `latest`
  - [ ] Deployed with `--region asia-southeast1 --port 8080`
  - [ ] Config injected via `--set-env-vars`: project, region, bucket, topic, model, allowed origins
  - [ ] No secret or config value baked into an image layer
  - [ ] The deploy command stops for confirmation — the `guard-cloud-commands` hook enforces this

### Story 6.3 — Runtime IAM
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] A dedicated runtime service account, not the default Compute Engine one
  - [ ] Exactly these five roles granted:

    | Capability               | Role                         |
    | ------------------------ | ---------------------------- |
    | Gemini via Vertex AI     | `roles/aiplatform.user`      |
    | Firestore                | `roles/datastore.user`       |
    | Pub/Sub alerts           | `roles/pubsub.publisher`     |
    | BigQuery climate queries | `roles/bigquery.jobUser`     |
    | GCS sample reads         | `roles/storage.objectViewer` |

  - [ ] No `roles/owner` or `roles/editor` — the hook blocks those bindings anyway
  - [ ] No service-account key file created; the container uses its runtime identity

### Story 6.4 — Post-deploy verification and rollback
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] `GET /api/health` on the deployed URL returns 200
  - [ ] `POST /api/analyze` against the deployed URL returns a payload that passes `validate_report.py`
  - [ ] A failed health check prints revision logs rather than a bare non-zero exit
  - [ ] Rollback documented and tested as a traffic shift to a previous revision — never a service delete
  - [ ] Service URL, revision name, and image digest reported after every deploy

## Definition of done

A revision serves traffic in `asia-southeast1`, both routes answer correctly over HTTPS, the runtime service account holds only the five roles, and rolling back to the previous revision has been performed at least once.

## Risks

| Risk                                          | Mitigation                                                              |
| --------------------------------------------- | ----------------------------------------------------------------------- |
| Build fails on missing `requirements.txt`     | Documented build context; the `docker-cloudrun` instructions enforce it |
| Container starts locally but not on Cloud Run | Must listen on `$PORT`; read revision logs before changing code         |
| 403 from Vertex AI or Pub/Sub after deploy    | Story 6.3 — grant the narrow role, never escalate to editor             |
| Credentials baked into an image layer         | `.dockerignore` plus no `COPY .env`                                     |
| Untraceable deployed revision                 | Tag with the git SHA                                                    |
| Dashboard blocked by CORS after deploy        | `ALLOWED_ORIGINS` must include the frontend origin                      |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Containerization and Cloud Run Deployment" --priority P1 \
  --description "Reproducible credential-free container serving on Cloud Run in asia-southeast1"
bl add --type story --parent EPIC-006 --priority P1 --estimate 3 --source requirements \
  --title "As an operator I can build a reproducible backend image" \
  --files backend/Dockerfile backend/.dockerignore \
  --ac "multi-stage python:3.11-slim build" "runs as a non-root user" \
       "builds from the repo root with -f backend/Dockerfile" "no credentials in any layer"
bl add --type story --parent EPIC-006 --priority P1 --estimate 3 --source requirements \
  --title "As an operator I can deploy the backend to Cloud Run" \
  --ac "image tagged with the git SHA" "config injected as env vars at deploy time" \
       "deployed to asia-southeast1 on port 8080"
bl add --type task --parent EPIC-006 --priority P1 --estimate 2 --source requirements \
  --title "Grant the runtime service account its five narrow roles" \
  --ac "dedicated service account" "no owner or editor binding" "no key file created"
bl add --type story --parent EPIC-006 --priority P1 --estimate 2 --source requirements \
  --title "As an operator I can verify a deploy and roll it back" \
  --ac "health returns 200 on the deployed URL" "analyze returns a contract-valid payload" \
       "rollback performed as a traffic shift to a previous revision"
```
