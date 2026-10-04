# Sprint 7 Report

Generated 2026-10-04T09:38:28+00:00
Goal: An analyst can review coordinate-based heat reports with attributed imagery, while report validation, API safeguards and offline QA provide reliable evidence without cloud spend.

## Delivery

- Committed: 7 item(s)
- Completed: 7
- Carried over: 0
- Open bugs: 0

| Item      | Type  | Priority | Status | Title                                                               |
| --------- | ----- | -------- | ------ | ------------------------------------------------------------------- |
| STORY-024 | story | P1       | done   | As a developer every API status code is covered                     |
| TASK-040  | task  | P1       | done   | Checklist and validate every new report-envelope field              |
| TASK-043  | task  | P1       | done   | Budget for stale tests when a sprint deliberately changes behaviour |
| TASK-044  | task  | P1       | done   | Prove attribution-required imagery is displayed by the dashboard    |
| TASK-045  | task  | P1       | done   | Require conclusive QA outcomes for long-running validation runs     |
| TASK-047  | task  | P2       | done   | Bound per-instance Maps request rate                                |
| TEST-002  | test  | P2       | done   | Raise Maps imagery client coverage to the 70 percent floor          |

## Tests

- Command: `/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/.venv/bin/python3 -m pytest tests -o addopts= --cov-config=/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/tests/coverage.ini --cov=backend --cov-report=term-missing --cov-report=json:/Users/hazra/Documents/Google_Hackathon/hotspot-sentinels/coverage.json -q --junit-xml=.pytest-report.xml`
- Result: **PASS**
- Summary: `655 passed, 3 warnings in 68.99s (0:01:08)`

## Coverage

- Configuration: `tests/coverage.ini` (backend application code)
- Total: **98.2%**

| File                                  | Covered |
| ------------------------------------- | ------- |
| backend/main.py                       | 96.3%   |
| backend/services/__init__.py          | 100.0%  |
| backend/services/alert_dispatcher.py  | 100.0%  |
| backend/services/database.py          | 100.0%  |
| backend/services/vision_analyzer.py   | 100.0%  |
| backend/tools/__init__.py             | 100.0%  |
| backend/tools/climate_service.py      | 95.2%   |
| backend/tools/maps_imagery_service.py | 97.9%   |
| backend/tools/seed_samples.py         | 98.9%   |
| backend/verify_setup.py               | 100.0%  |

## Retrospective

### What went well

- All 7 items committed at planning (15 points) were delivered, with no carry-over. The authoritative suite command, `python3 -m pytest -o addopts='' -q`, completed **PASS: 655 tests**. Coverage rose from 90.4% to 98.2% (+7.8 percentage points); the number of backend files below the 70% floor fell from one to zero, including `maps_imagery_service.py` from 37.8% to 97.9%.
- Scope expansion was explicitly rebaselined rather than hidden: six human-directed items added 12 points (TASK-022, TASK-038, STORY-022, TASK-031, BUG-025 and BUG-026). Total output was 27 points against the original 15-point commitment. The zero-open-bug result followed the fixes and verification; it does not erase the severity of the defects found.
- The backend and frontend both reached verified Cloud Run revisions in `asia-southeast1` (`hotspot-backend-00005-fl7` and `hotspot-frontend-00004-59q`). Health and scans routes worked, all four dependencies reported ready, and a live coordinate analysis persisted a canonical-valid HIGH report with Google Maps imagery and BigQuery climate data. The dashboard browser run displayed the actual attributed image and provenance. Rejection cases returned 415, 422, 422, 422 and 502 with generic client errors; production logs contained no API-key occurrence, `AIza` string or traceback.

### What did not go well

- **Frontend deployment was unverified for three sprints.** BUG-026 was not an isolated startup hiccup: every prior container proof exercised only `backend/Dockerfile`. Buildpacks launched Streamlit as a gunicorn WSGI app, the sprint 4 dependency split meant Streamlit was absent from the default environment, and `API_BASE_URL` was unset. No release check exercised the frontend URL, so a dead dashboard coexisted with backend-only deployability claims. This scope gap is tracked by new TASK-051; future release evidence must prove frontend startup, health, configuration and an end-to-end coordinate run separately from backend proof.
- **Documentation drift reached executable deployment code for the first time.** BUG-025 is the fourth recurrence of this class and had four independent fatal defects in `deploy.sh`: wrong build context, omitted `GOOGLE_MAPS_API_KEY` and `BIGQUERY_LOCATION`, wrong default service name, and no `linux/amd64` platform pin. The skill's triage table described the build-context failure while the script contradicted it further down. No offline test inspected the script. Existing TASK-048 tracks the deploy-script lint; it is not duplicated here.
- **Stale-test churn recurred for a fifth consecutive sprint.** TASK-038's approved removal of the two legacy smoke scripts invalidated three assertions; TASK-045's behavior change invalidated one more. TASK-043's phase-4 rule was added during sprint 7, after this sprint's planning, so it could not have prevented sprint-7 churn as run. Applied prospectively before work starts, it should identify the TASK-045 assertion and budget its update. It cannot predict TASK-038's later human-approved scope addition without a second control at the point of change. New TASK-052 extends the rule: identify invalidated tests and rebaseline estimate/capacity before authorized mid-sprint work begins.
- **Seven sprints of work remain without a commit or remote.** `git rev-list --all --count` is zero. The entire project exists as an uncommitted working tree on one machine; there is no backup or recoverable history, and the 2026-10-11 submission deadline is one week away. `.gitignore` was checked for `.env`, `.venv/`, `data_samples/` and `__pycache__/`, but a reviewed initial commit and push have not happened. Existing TASK-049 is an unstarted P0 and is an existential risk to the submission.
- **The default demo opens on the wrong first impression.** Coordinates 1.3521/103.8198 resolve to dense canopy and correctly score LOW. That is valid product behavior but weak framing for a three-minute urban-heat demo. Existing TASK-050 tracks the cached HIGH-risk opening location at 1.3343/103.8563, a critical-alert walkthrough, and a contrasting LOW-risk location.
- **A packaging acceptance test is tied to local machine state.** A test compares source hashes against the locally built `hotspot-hardened:latest` image; it required a manual `docker build -f backend/Dockerfile -t hotspot-hardened:latest backend` refresh during the sprint. A clean machine or CI may not have that tag, and a stale image does not prove the current source. New TASK-053 tracks reproducible, source-tied packaging evidence with unavailable Docker treated as inconclusive rather than a pass.

### Retro items

- Existing: TASK-048 (offline deploy-script lint), TASK-049 (P0 version-control recovery), and TASK-050 (demo coordinates). No duplicates were filed.
- New: TASK-051 (frontend deployment proof), TASK-052 (mid-sprint stale-test/change-control budgeting), and TASK-053 (clean-machine packaging evidence).

### Sign-off implication

The sprint's planned goal and all deployed acceptance evidence were achieved, and all committed sprint items are done. The mechanical gate must nevertheless reject sign-off while TASK-049 remains an open P0: the uncommitted working tree is the only copy of seven sprints of work. Do not treat a green test suite or successful Cloud Run deployment as a substitute for preserving the source.
