# EPIC-09 — Demo, Documentation & Submission

|                |                                                                                                                          |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Goal**       | A judge can understand what HotSpot Sentinels does, watch it work, and verify the claims — without the team in the room. |
| **Source**     | Google Cloud AI Builder Cup deliverable; not scoped in the original backlog                                              |
| **Priority**   | P1                                                                                                                       |
| **Status**     | Not started                                                                                                              |
| **Depends on** | EPIC-06, EPIC-07, EPIC-08                                                                                                |
| **Delivers**   | `README.md`, architecture diagram, demo runbook, submission package                                                      |

## Why this epic exists

The backlog ended at "build the dashboard". The competition does not score a repository — it scores a submission. A working product nobody can evaluate is worth the same as no product.

Budget real sprint capacity for this. It is the one epic that cannot be done at the last minute, because recording a demo exposes every rough edge in the other eight.

## Scope

**In:** project README, architecture diagram, demo script and runbook, reset procedure, submission checklist.

**Out:** new product features. If the demo reveals a defect, it becomes a bug in the owning epic — not a patch inside this one.

## Stories

### Story 9.1 — Project README
- **File:** `README.md`
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Opens with the problem, the approach, and the "Sustainability and Social Impact" theme fit in under 200 words
  - [ ] Setup in copy-pasteable commands: venv, `pip install -r requirements.txt`, `./setup_gcp.sh`, `verify_setup.py`, uvicorn, streamlit
  - [ ] States the stack explicitly: Gemini 2.5 Flash on Vertex AI, Cloud Run, Firestore, Pub/Sub, BigQuery, `asia-southeast1`
  - [ ] Links the deployed URL and the epic catalogue
  - [ ] Contains no secrets, no project IDs, and no screenshots with a project ID visible

### Story 9.2 — Architecture diagram
- **File:** `README.md` or `.github/docs/architecture.md`
- **Estimate:** 2 · **Priority:** P2 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Mermaid diagram showing image upload → FastAPI → Gemini → Firestore + Pub/Sub → dashboard
  - [ ] BigQuery telemetry shown feeding the analysis
  - [ ] The critical-HVI alert path visually distinct
  - [ ] Matches the real call flow in `main.py` — an aspirational diagram is a defect

### Story 9.3 — Demo runbook
- **File:** `.github/docs/demo-runbook.md`
- **Estimate:** 3 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Pre-flight checklist: environment doctor green, smoke test passing, samples seeded, services warm
  - [ ] A scripted narrative hitting both extremes — green park scoring low, industrial asphalt scoring critical and firing the alert banner
  - [ ] Timed to the submission limit with the one cut-first section identified
  - [ ] A reset procedure returning the system to a clean state between runs
  - [ ] A fallback for each likely live failure: no network, quota exhausted, cold-start latency
  - [ ] Rehearsed end to end at least once before recording

### Story 9.4 — Submission package
- **Estimate:** 2 · **Priority:** P1 · **Status:** Not started
- **Acceptance criteria:**
  - [ ] Repository public or shared as the rules require, with no secrets in history
  - [ ] Deployed Cloud Run URL reachable and warm
  - [ ] Demo recording produced and uploaded
  - [ ] Every competition form field completed
  - [ ] Final `contract-auditor` run is clean and the latest sprint report is committed
  - [ ] Submitted before the deadline, not at it

## Definition of done

A reviewer following only the README reaches a working local instance; the deployed URL answers; the recording shows both the low and critical paths; and the submission is accepted.

## Risks

| Risk                                            | Mitigation                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------------ |
| Secrets in git history discovered at submission | `.gitignore` from EPIC-01 before the first commit; audit history before going public |
| Live demo failing on stage                      | Record it; keep the runbook's fallbacks ready                                        |
| Cloud Run cold start stalling the opening       | Warm the service in the pre-flight checklist                                         |
| Quota exhausted mid-demo                        | `climate_service` falls back silently; pre-generate a captured payload as a backstop |
| Demo reveals a defect too late                  | Rehearse a full sprint before the deadline                                           |
| Diagram drifting from the real flow             | Story 9.2 is verified against `main.py`                                              |

## Seed the backlog

```bash
bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }
bl add --type epic --title "Demo, Documentation and Submission" --priority P1 \
  --description "README, architecture diagram, rehearsed demo runbook and the submission package"
bl add --type story --parent EPIC-009 --priority P1 --estimate 2 --source requirements \
  --title "As a judge I can understand and run the project from the README alone" \
  --files README.md \
  --ac "problem, approach and theme fit stated up front" "copy-pasteable setup commands" "no secrets or project IDs"
bl add --type story --parent EPIC-009 --priority P2 --estimate 2 --source requirements \
  --title "As a judge I can see how the system fits together" \
  --ac "mermaid diagram of the real call flow" "critical alert path visually distinct"
bl add --type story --parent EPIC-009 --priority P1 --estimate 3 --source requirements \
  --title "As a presenter I can run the demo reliably end to end" \
  --files .github/docs/demo-runbook.md \
  --ac "pre-flight checklist" "scripted low and critical scenarios" "reset procedure" \
       "fallback for each likely failure" "rehearsed at least once"
bl add --type task --parent EPIC-009 --priority P1 --estimate 2 --source requirements \
  --title "Assemble and submit the competition package" \
  --ac "repository shared with no secrets in history" "deployed URL reachable" \
       "recording uploaded" "contract audit clean"
```
