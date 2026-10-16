# Submission Checklist

Competition: Google Cloud AI Builder Cup — Sustainability and Social Impact.
Prototype module closes **2026-10-18**. An earlier revision of this file recorded
2026-10-11, which was wrong; the date below comes from the live submission portal.

## Acceptance criteria (TASK-006)

| Criterion                                    | State                              | Evidence                                                                                                                                                                                                                                                                  |
| -------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repository shared with no secrets in history | **MET**                            | `github.com/debabratahazra/hotspot-sentinels`, public. gitleaks v8.21.2 scanned the full history: no leaks, and it now runs as a required check on every push and pull request. `.env` never committed; `.env.example` carries `GOOGLE_MAPS_API_KEY` with an empty value. |
| Deployed URL reachable                       | **MET**                            | `/api/live` 200, `/api/health` `operational` with gemini, firestore, pubsub and bigquery all `ready`. Frontend `/_stcore/health` ok.                                                                                                                                      |
| Contract audit clean                         | **MET** — see reconciliation below | Full audit run 2026-10-04; no finding survived reconciliation as a genuine contract violation.                                                                                                                                                                            |
| Recording uploaded                           | **MET**                            | Recorded, uploaded unlisted and verified reachable signed-out: the YouTube oEmbed endpoint resolves the title without credentials, which it refuses to do for a Private video. The URL is on slide 13 of the deck.                                                        |

**Submitted 2026-10-16.** All four acceptance criteria are met.

## Live system

|                   |                                                                          |
| ----------------- | ------------------------------------------------------------------------ |
| Dashboard         | https://hotspot-frontend-153692178986.asia-southeast1.run.app            |
| Backend           | https://hotspot-backend-153692178986.asia-southeast1.run.app             |
| Backend revision  | `hotspot-backend-00035-c5s`                                              |
| Frontend revision | `hotspot-frontend-00030-vtq`                                             |
| Runtime identity  | `hotspot-run@…` — six narrow roles, no editor or owner, zero key files   |
| Region            | `asia-southeast1` (sole exception: `BIGQUERY_LOCATION=US` for NOAA GSOD) |

## Quality evidence

|                 |                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Tests           | 685 passing, fully offline                                                                                                      |
| Coverage        | 98.2%, no file below the 70% floor                                                                                              |
| Open P0 defects | 0                                                                                                                               |
| CI              | five required checks green on every push and pull request                                                                       |
| Release         | keyless — a `vMAJOR.MINOR.PATCH` tag deploys both services through Workload Identity Federation, with zero service-account keys |
| Branch policy   | `main` protected: pull request required, all five checks must pass, no force push, no deletion                                  |

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

## Scope not delivered

Stated plainly rather than omitted. None of these is a defect; each needs a human decision or unimplemented feature work.

| Item        | Missing                                                                                            | Impact on the submission                                                                                                       |
| ----------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `STORY-031` | scan records linked to retained imagery                                                            | None. `TASK-046` introduced durable imagery storage under deterministic prefixes, but a scan record carries no object URI yet. |
| `TASK-011`  | correction of the human-owned `.github/COPILOT_GUIDE.md` and `.github/docs/epics/Epics_Stories.md` | None on the running system; those documents carry statements predating later ratified decisions.                               |

`STORY-043` and `TASK-046` were closed on 2026-10-05 and verified live — see Quality evidence above.

## Submitted

Submitted on **2026-10-16**, two days inside the 2026-10-18 close.

Re-verified on the day of submission rather than assumed from an earlier sprint:
`/api/health` returned `operational` with gemini, firestore, pubsub and bigquery
all `ready`, on revisions `hotspot-backend-00035-c5s` and
`hotspot-frontend-00030-vtq`.

No autoscaling restore was needed. Both services already run at `maxScale=3`;
the demo stopped pinning `--max-instances=1` once `TASK-046` moved the imagery
cache into Cloud Storage, so there was no demo-time setting left to undo.
