---
name: gcp-environment-doctor
description: 'Diagnose HotSpot Sentinels environment and Google Cloud setup problems. Use when a script or service fails with authentication, credential, permission, 403, 404, quota, "API not enabled", "project not set", DefaultCredentialsError, missing bucket, missing Pub/Sub topic, or missing Firestore database errors — or when verify_setup.py, the FastAPI backend, or the Streamlit app will not start locally.'
argument-hint: "Paste the error, or run with no argument for a full environment check"
---

# GCP Environment Doctor

Diagnose before you change anything. Most failures here are configuration, not code.

## First move

```bash
python3 .github/skills/gcp-environment-doctor/scripts/doctor.py
```

The [doctor script](./scripts/doctor.py) is read-only. It checks `.env` completeness, the mandated region and model, installed Python packages, gcloud auth, Application Default Credentials, project alignment, enabled APIs, and the existence of the bucket, topic, and Firestore database. Each failure comes with the exact fix command. Add `--json` for machine-readable output.

Run it before proposing any fix — a guessed diagnosis wastes more time than the 20 seconds this takes.

## Error map

| Symptom                                | Cause                               | Fix                                                                                    |
| -------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------- |
| `DefaultCredentialsError`              | No Application Default Credentials  | `gcloud auth application-default login`                                                |
| `403 PermissionDenied` on Vertex AI    | Missing role or wrong project       | Grant `roles/aiplatform.user`; confirm the project matches `.env`                      |
| `403` publishing to Pub/Sub            | Missing `roles/pubsub.publisher`    | Grant it to the caller or runtime service account                                      |
| `SERVICE_DISABLED` / "API not enabled" | API off in this project             | `gcloud services enable <api>.googleapis.com`                                          |
| `404` on the model                     | Model unavailable in the region     | Region must be `asia-southeast1` and model `gemini-2.5-flash`                          |
| `404 NotFound` on a bucket or topic    | Resource never provisioned          | Re-run `./setup_gcp.sh`                                                                |
| `429` / quota exceeded                 | Rate or quota limit                 | Back off and retry; for BigQuery let `climate_service` use its offline fallback        |
| `ModuleNotFoundError: google.genai`    | Wrong interpreter or missing deps   | `source venv/bin/activate && pip install -r requirements.txt`                          |
| Firestore `NOT_FOUND` on write         | Database never created              | `gcloud firestore databases create --location=asia-southeast1 --type=firestore-native` |
| Works locally, 403 on Cloud Run        | Runtime service account lacks roles | Grant the five runtime roles — see the `cloud-deployer` agent                          |

## Procedure

1. Run the doctor. Fix what it reports, highest-impact first — auth before APIs, APIs before resources.
2. Re-run the doctor to confirm the fix landed.
3. Confirm end to end with `python backend/verify_setup.py`.
4. If the doctor is all green but the error persists, it is a code problem, not an environment one — hand off to the `contract-auditor` agent.

## Constraints

- DO NOT create service-account key files. This project uses Application Default Credentials only.
- DO NOT print `.env` contents, tokens, or full cloud error payloads into the transcript.
- DO NOT fix a permission error by granting `roles/owner` or `roles/editor`. Grant the specific role.
- DO NOT run `./setup_gcp.sh` yourself — it mutates cloud resources and needs an interactive login. Tell the user to run it.
