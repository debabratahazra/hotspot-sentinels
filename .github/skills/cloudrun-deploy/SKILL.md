---
name: cloudrun-deploy
description: "Build, push, and deploy the HotSpot Sentinels backend to Cloud Run in asia-southeast1, then verify and if needed roll back. Use when shipping the FastAPI service, creating the Artifact Registry repository, wiring runtime environment variables, granting runtime service-account IAM roles, diagnosing a failed revision or container startup error, or routing traffic back to a previous revision."
argument-hint: "deploy | verify | rollback | iam"
---

# Cloud Run Deployment

Region is always `asia-southeast1`. Container port is always 8080.

## Before you deploy

1. The build must be green. Run the `pipeline-smoke-test` skill first — never deploy a failing build.
2. `.env` must be complete. Run the `gcp-environment-doctor` skill if unsure.
3. Confirm with the user. The [deploy script](./scripts/deploy.sh) mutates cloud infrastructure and `.github/hooks/guard-cloud-commands.json` will ask for confirmation. Never work around the hook.

## Deploy

```bash
bash .github/skills/cloudrun-deploy/scripts/deploy.sh
```

Extra `gcloud run deploy` flags pass straight through, for example `--no-allow-unauthenticated` or `--service-account hotspot-run@PROJECT.iam.gserviceaccount.com`.

The script creates the Artifact Registry repo if missing, then builds **each service from its own directory as the build context** — `docker build -f backend/Dockerfile backend` and `docker build -f frontend/Dockerfile frontend` — pushes a git-SHA tag, deploys with env vars injected at runtime, and health-checks the result, dumping revision logs if the check fails. Each Dockerfile's `COPY` paths are relative to its own directory, and each directory has its own `.dockerignore` protecting exactly that context. Builds pass `--platform linux/amd64`, because Cloud Run rejects the arm64 image an Apple-silicon host produces by default.

The services are `hotspot-backend` (override with `SERVICE_NAME`) and `hotspot-frontend`. Deploying under any other name creates a second service rather than a new revision. Each is verified on its own endpoint — the backend on `/api/health`, the frontend on `/_stcore/health` — because a healthy backend is not evidence that the dashboard works. The frontend receives the backend's resolved URL as `API_BASE_URL`.

Nothing secret is baked into the image. Project, region, bucket, topic, model, allowed origins, `BIGQUERY_LOCATION` and `GOOGLE_MAPS_API_KEY` all arrive as Cloud Run environment variables. The script aborts if `GOOGLE_MAPS_API_KEY` is unset, because coordinate analysis returns 502 without it.

## Runtime IAM

Grant the runtime service account exactly these, and nothing broader:

| Capability               | Role                         |
| ------------------------ | ---------------------------- |
| Gemini via Vertex AI     | `roles/aiplatform.user`      |
| Firestore                | `roles/datastore.user`       |
| Pub/Sub alerts           | `roles/pubsub.publisher`     |
| Pub/Sub readiness probe  | `roles/pubsub.viewer`        |
| BigQuery climate queries | `roles/bigquery.jobUser`     |
| GCS sample reads         | `roles/storage.objectViewer` |

`roles/pubsub.viewer` is required in addition to `publisher` because `/api/health`
calls `get_topic`, and `publisher` grants only `pubsub.topics.publish`. Without it
the service answers `degraded` with `pubsub: unavailable` while publishing still
works. Verified on 2026-10-04.

The runtime account is `hotspot-run@PROJECT.iam.gserviceaccount.com`. Prefer it over
the default Compute Engine account, which carries `roles/editor`. Never grant
`roles/owner` or `roles/editor` to clear a 403 — the hook blocks that anyway.

## Verify

```bash
URL=$(gcloud run services describe hotspot-backend --region asia-southeast1 --format='value(status.url)')
curl -fsS "$URL/api/health"
curl -fsS -X POST "$URL/api/analyze" -F "image=@data_samples/industrial_asphalt.png" -F "ambient_temp_c=36.5" \
  | python3 .github/skills/heat-report-validation/scripts/validate_report.py -
```

A deploy is not done until `/api/analyze` returns a contract-valid payload from the deployed URL.

## Rollback

Roll back by shifting traffic, never by deleting the service:

```bash
gcloud run services update-traffic hotspot-backend --region asia-southeast1 --to-revisions <previous>=100
```

## Triage

| Symptom                                     | Cause                                                                                                      |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Build fails on `requirements.txt` not found | Built from the repo root — the context must be the service's own directory, as `docker build -f backend/Dockerfile backend` or `docker build -f frontend/Dockerfile frontend` |
| Container fails to start                    | Not listening on `$PORT`/8080, or an import-time crash; read the revision logs                             |
| 403 from Vertex AI                          | Runtime SA missing `roles/aiplatform.user`                                                                 |
| 403 publishing alerts                       | Runtime SA missing `roles/pubsub.publisher`                                                                |
| Health OK but analyze 502                   | `VisionAnalysisError` — model, region, or quota; check server logs, not the client response                |
| Coordinate analyze 502, upload analyze fine | `GOOGLE_MAPS_API_KEY` missing from the revision, or the key is not authorised for the Maps Static API      |
| CORS errors from the dashboard              | `ALLOWED_ORIGINS` missing the frontend origin                                                              |

## Constraints

- DO NOT delete Cloud Run services, buckets, topics, or Firestore data. Roll back traffic instead.
- DO NOT create service-account key files.
- DO NOT echo `.env` contents or auth tokens into the transcript.
- DO NOT edit application code to force a deploy through. Hand the defect back as a bug.
