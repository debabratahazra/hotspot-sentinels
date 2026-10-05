# Submission Checklist

Competition: Google Cloud AI Builder Cup — Sustainability and Social Impact.
Deadline **2026-10-11**. Every claim below was verified on 2026-10-04, not assumed.

## Acceptance criteria (TASK-006)

| Criterion                                    | State                              | Evidence                                                                                                                                                                                           |
| -------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repository shared with no secrets in history | **MET**                            | `github.com/debabratahazra/hotspot-sentinels`, public. gitleaks v8.21.2 scanned all 8 commits: no leaks. `.env` never committed; `.env.example` carries `GOOGLE_MAPS_API_KEY` with an empty value. |
| Deployed URL reachable                       | **MET**                            | `/api/live` 200, `/api/health` `operational` with gemini, firestore, pubsub and bigquery all `ready`. Frontend 200.                                                                                |
| Contract audit clean                         | **MET** — see reconciliation below | Full audit run 2026-10-04; no finding survived reconciliation as a genuine contract violation.                                                                                                     |
| Recording uploaded                           | **OUTSTANDING**                    | Needs a human. Follow [demo-runbook.md](../.github/docs/demo-runbook.md).                                                                                                                          |

**One item remains: the recording.** Everything else is done and evidenced.

## Live system

|                   |                                                                          |
| ----------------- | ------------------------------------------------------------------------ |
| Dashboard         | https://hotspot-frontend-153692178986.asia-southeast1.run.app            |
| Backend           | https://hotspot-backend-153692178986.asia-southeast1.run.app             |
| Backend revision  | `hotspot-backend-00006-8ds`                                              |
| Frontend revision | `hotspot-frontend-00005-ntr`                                             |
| Region            | `asia-southeast1` (sole exception: `BIGQUERY_LOCATION=US` for NOAA GSOD) |

## Quality evidence

|                 |                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------- |
| Tests           | 656 passing, fully offline                                                                |
| Coverage        | 98.2%, no file below the 70% floor                                                        |
| Open P0 defects | 0                                                                                         |
| CI              | GitHub Actions green on every push — suite, coverage gate, both image builds, secret scan |

## Contract audit reconciliation

The audit initially reported one blocker, three major and two minor findings. Each
was checked against the code before being accepted, per the project rule that a
specification is reconciled before a failure is triaged. **None survived as a
genuine contract violation.**

| Reported                                                            | Outcome                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.env.example` missing                                              | **False positive.** The file exists (1032 bytes) and is tracked by git. The auditing tool could not read it because of the editor's file-ignore on `.env.example` — the long-standing TASK-022 condition.                                                                          |
| Canonical validator re-derives HVI bands                            | **By design.** The validator is an independent oracle; importing `risk_level_for_score` would make it unable to detect a bug in that function. The "sole classifier" rule governs application layers, not the external validator. The audit itself confirmed the thresholds match. |
| `doc_id` not persisted inside the Firestore document                | **By design.** The document ID is the record's key; storing it again as a field is redundant. It is populated on the API response at `main.py:362`.                                                                                                                                |
| `alert_dispatcher` has no service exception type                    | **Not a violation.** `dispatch_heat_alert` catches `(ValueError, OverflowError)` internally and returns `''`. No exception crosses a layer boundary at all, which is stricter than the convention requires.                                                                        |
| Frontend does not show `identity_source` provenance for `zone_name` | **Enhancement, not a violation.** The contract requires the *report* to expose provenance, which it does. The dashboard already surfaces `climate_source` and `image_source` provenance; extending that to identity would be an improvement, not a fix.                            |
| `setup_gcp.sh` hardcodes the Pub/Sub topic                          | **Cosmetic.** It is a provisioning script that establishes the default environment and writes `.env`. Accepting an override would be tidier but breaks no contract.                                                                                                                |

Areas confirmed clean with no findings: metric units, GenAI SDK usage
(`from google import genai`, `gemini-2.5-flash` via `MODEL_ID`), region defaults,
layering, the Maps request budget, and both CI workflows.

## Before submitting

1. Record the demo with [demo-runbook.md](../.github/docs/demo-runbook.md) — run the pre-flight first; the imagery cache goes cold when Cloud Run scales to zero.
2. Re-verify the deployed URL on the day. A revision that was healthy a week earlier is not evidence it is healthy now.
3. Restore autoscaling after recording: `gcloud run services update hotspot-backend --region asia-southeast1 --max-instances=3`.
