# Sprint 3 Report

Generated 2026-10-03T07:10:25+00:00
Goal: An analyst can upload an aerial image in the dashboard, receive a rubric-consistent heat report with labelled climate data, persisted history and truthful alert status, and use the repaired service deployed from a hardened image.

## Delivery

- Committed: 23 item(s)
- Completed: 22
- Carried over: 1
- Open bugs: 1

### Commitment and velocity

- Original commitment: 46 points / 23 items, human-authorised at 2.2 times sprint 2's measured 21-point velocity.
- Completed original commitment: 43 points / 22 items. STORY-017 (3 points) remains partial because its temperature-slider criterion is unmet; STORY-033 tracks the backend override and UI wiring.
- Unplanned completed work: BUG-023 and BUG-024, 1 point each, outside the original commitment. Total delivery: 45 points / 24 items against 48 points / 25 items of actual scope. Do not rewrite the original commitment or count STORY-017 as done.
- Next capacity baseline: 45 completed points, explicitly including 2 unplanned points; this is one observed stretch sprint, not proof of sustainable capacity.

| Item      | Type  | Priority | Status    | Title                                                                         |
| --------- | ----- | -------- | --------- | ----------------------------------------------------------------------------- |
| STORY-003 | story | P1       | done      | As an analyst I can trust the HVI rubric to rank zones consistently           |
| STORY-005 | story | P1       | done      | As an operator the product still works when BigQuery is unavailable           |
| STORY-007 | story | P1       | done      | As an ops lead I am alerted automatically when a zone becomes critical        |
| STORY-008 | story | P1       | done      | As an auditor I can trust the alert_dispatched flag on a stored scan          |
| STORY-009 | story | P2       | done      | As an operator I can check whether the service and its dependencies are ready |
| STORY-010 | story | P2       | done      | As an analyst I can upload an aerial image and receive a full heat report     |
| STORY-011 | story | P1       | done      | As an operator the API rejects unsafe uploads before spending cloud budget    |
| STORY-012 | story | P1       | done      | As a frontend developer I get usable errors without leaked internals          |
| STORY-013 | story | P1       | done      | As an analyst I can list recent scans                                         |
| STORY-017 | story | P3       | in_review | As an analyst I can choose a city, temperature and image and run an analysis  |
| STORY-018 | story | P3       | done      | As an analyst I can see the HVI score and risk level at a glance              |
| STORY-019 | story | P3       | done      | As a city planner I can read the passive cooling blueprint                    |
| STORY-020 | story | P3       | done      | As an ops lead I see confirmation that a critical alert was dispatched        |
| STORY-021 | story | P3       | done      | As a user the dashboard stays readable when something goes wrong              |
| TASK-013  | task  | P3       | done      | Deploy and verify the repaired sprint 2 build on Cloud Run                    |
| TASK-016  | task  | P0       | done      | Verify generated artefacts in the actual workspace before handoff             |
| TASK-017  | task  | P0       | done      | Require regression tests when exception or validation coverage narrows        |
| TASK-021  | task  | P0       | done      | Reject verification evasion and require discoverable test names               |
| TASK-025  | task  | P1       | done      | Harden the Dockerfile to the multi-stage non-root contract                    |
| BUG-019   | bug   | P0       | done      | Missing-project SDK failure bypasses every degradation policy                 |
| TASK-026  | task  | P2       | done      | Declare a response model for POST /api/analyze                                |
| TASK-027  | task  | P1       | done      | Document climate_source and the BigQuery location exception in the contract   |
| TASK-028  | task  | P0       | done      | Enforce a standing cross-layer compatibility gate for contract changes        |

## Tests

- Result: **PASS**
- Summary: **361 passed**, zero failures, errors or skips, verified from the generated .pytest-report.xml. Sprint 2 had 251 passing tests; growth is 110. The generator selected the coverage footer instead of the pytest summary; this statement records the executable result.

## Coverage

- Total: **89.3%**
- Delta: -1.6 percentage points from sprint 2's 90.9%. The denominator includes new code and two legacy manual scripts at 0%; excluding those scripts yields 95.4%. The official whole-backend result remains 89.3%.
- Every sprint-touched executable file exceeds the 70% floor. Alert dispatch is 84.4% and climate telemetry is 87.1%; invalid-payload validation paths still need coverage.

| File                                 | Covered |
| ------------------------------------ | ------- |
| backend/main.py                      | 97.5%   |
| `backend/services/__init__.py`       | 100.0%  |
| backend/services/alert_dispatcher.py | 84.4%   |
| backend/services/database.py         | 100.0%  |
| backend/services/vision_analyzer.py  | 100.0%  |
| backend/test_analyzer.py             | 0.0%    |
| backend/test_pipeline.py             | 0.0%    |
| `backend/tools/__init__.py`          | 100.0%  |
| backend/tools/climate_service.py     | 87.1%   |
| backend/tools/seed_samples.py        | 98.9%   |
| backend/verify_setup.py              | 100.0%  |

Below the 70% floor — needs test tasks next sprint:

- backend/test_analyzer.py
- backend/test_pipeline.py

## Open bugs carried forward

- BUG-006 (P2) Report validator accepts timezone-naive and non-UTC timestamps

## Live delivery evidence

Evidence supplied by the deployment and validation handoff, not rerun during phases 9-10:

- Revision hotspot-backend-00003-vfh serves 100% of traffic at <https://hotspot-backend-153692178986.asia-southeast1.run.app>. gcloud reported "Building using Dockerfile", not buildpacks; the hardened Dockerfile was used.
- /api/health returned operational with gemini, firestore, pubsub and bigquery ready.
- Real Gemini analysis of industrial_hotspot.jpg returned HVI 8.6 / CRITICAL, climate_source=bigquery with live NOAA telemetry at 31.0 degrees C, alert_dispatched=true from a real Pub/Sub publish, a doc_id, and surface percentages totalling 100. validate_report.py accepted the payload.
- text/plain upload was rejected with HTTP 415.
- Supplied gate result: exit 1, solely committed_items_done for STORY-017. nothing_blocked, no_open_p0 and sprint_report_written passed. No gate was run in phases 9-10; sign-off belongs to the orchestrator.

## Retrospective Evidence

Keep the practices: 22/23 original items delivered at a human-authorised 2.2x stretch with the real cloud pipeline working; TASK-028 rejected all four historical defects in its negative proof and caught stale manual-script fields and an unawaited coroutine; deferred TASK-016/017/021 became written verification rules; SQL injection, wildcard CORS, absent dockerignore, root container execution and unbounded uploads were closed, several with real Docker builds.

Be blunt about failures: BUG-024 was found only by deploying because current-schema-only fixtures concealed legacy Firestore records that made strict history response validation return HTTP 500. 361 green tests encoded assumptions, not production history. QA mis-attributed committed-scope failures and P0 parents for the second sprint while TASK-029 remained unscheduled. Four P0 reports reflected stale criteria or documentation, including WebP versus the ratified JPEG/PNG contract, NFR-1's missing BigQuery exception and obsolete repository-root deploy instructions. STORY-017 did not meet its slider criterion. Capacity discipline broke again: 46 points was already a stretch and emergency work added two more points.

Improve: cover realistic legacy-shaped history through the actual response boundary while keeping newly generated analysis strict; make a post-deploy smoke step mandatory, including history as well as health and analysis; address the 1.6pp coverage fall, 0%-covered manual scripts and invalid-payload branches; obtain OQ-4 human answers before EPIC-009; remove frontend dependencies from the 899 MB backend image through TASK-032. Follow-up IDs and priorities are recorded in the phase-10 reconciliation below.

## Phase 10 Reconciliation

| Finding                                                    | Backlog action                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| W1: 22/23 at authorised stretch; real cloud pipeline works | Keep demonstrated live verification practice; no item.                                                                                                                                                                                                                               |
| W2: TASK-028 caught four historical and two live defects   | Keep the standing cross-layer gate and negative proof; no item.                                                                                                                                                                                                                      |
| W3: TASK-016/017/021 written rules finally landed          | Keep the written verification rules; no item.                                                                                                                                                                                                                                        |
| W4: Security hardening closed, with real builds            | Keep real Docker verification; no item.                                                                                                                                                                                                                                              |
| R1: BUG-024 found only after deploy                        | TASK-035 (new task, P1, 2 points): mixed-vintage history through actual response validation and a negative proof. TASK-036 (new task, P1, 2 points): mandatory post-deploy smoke evidence. BUG-024 remains done; no duplicate bug.                                                   |
| R2: QA attribution recurred                                | TASK-029 (existing task, P2 -> P1, 1 point); explicit recurrence note, existing criteria retained.                                                                                                                                                                                   |
| R3: Four P0 reports were stale criteria/documentation      | TASK-018 (existing task, P2 -> P1, 1 point); ratified-source reconciliation before QA triage, without protected-doc edits.                                                                                                                                                           |
| R4: STORY-017 partial, slider criterion unmet              | TASK-018 owns honest criterion handoff. STORY-033 (existing delivery story, P2 -> P1, 2 points) precedes STORY-017 (P3 -> P1, 3 points), the sole carry-over. No duplicate story or completion credit.                                                                               |
| R5: Capacity discipline recurred                           | TASK-030 (existing task, P2 -> P1, 2 points); emergency swaps/rebaseline and prevention reserve, with original versus actual accounting.                                                                                                                                             |
| I1: Coverage fall, legacy scripts and invalid branches     | TEST-001 (existing test item, P2, 1 point) owns denominator/manual-script disposition with existing EPIC-008 work. TASK-033 (new task, EPIC-004, P2, 1 point) owns alert invalid-payload branches; TASK-034 (new task, EPIC-003, P2, 1 point) owns climate invalid-payload branches. |
| I2: OQ-4 blocks all EPIC-009                               | TASK-031 (existing task, blocked/P1, 1 point); needs human answers, no invented deadline or duplicate submission scope.                                                                                                                                                              |
| I3: Backend image is 899 MB                                | TASK-032 (existing task, P2, 2 points); original validation provenance retained, no duplicate container item.                                                                                                                                                                        |
| I4: Missing realistic legacy-schema test                   | TASK-035 also covers this finding; no duplicate test item.                                                                                                                                                                                                                           |

All converted follow-ups have source=retro. Existing descriptions retain provenance. New tasks remain new pending grooming and specialist delegation; no production code or tests were written, and no backlog item was marked done.

The retrospective close command was:

```bash
bl close-sprint \
--went-well \
"W1: 22/23 original items delivered at a human-authorised 2.2x stretch; the real Google Cloud pipeline works." \
"W2: TASK-028 rejected four historical defects and caught stale manual-script fields and an unawaited coroutine immediately." \
"W3: Twice-deferred TASK-016/017/021 landed as written verification rules." \
"W4: SQL injection, wildcard CORS, missing dockerignore, root container execution and unbounded uploads closed; several verified by real Docker builds." \
--went-wrong \
"R1: BUG-024 was found only by deploying: strict history response validation rejected legacy Firestore records; 361 current-schema-only tests missed production history. Prevention: TASK-035/036." \
"R2: QA again blocked committed work over uncommitted criteria and filed P0s under wrong parents; deferred TASK-029 recurred and is promoted to P1." \
"R3: Four P0 reports were stale criteria or documentation drift, including WebP, the BigQuery exception and backend build context; TASK-018 promoted to P1." \
"R4: STORY-017 shipped partial: its slider was removed because analyze accepts only file. TASK-018 owns honest criterion handoff; STORY-033 closes the delivery gap." \
"R5: Capacity discipline broke again: 46 planned points versus prior velocity 21, plus 2 unplanned bug points; 43 committed points completed, 45 total. TASK-030 promoted to P1." \
--improve \
"I1: Coverage fell 1.6pp to 89.3%; excluding two 0%-covered manual scripts gives 95.4%, not the official total. TEST-001 tracks denominator disposition; TASK-033/034 cover alert 84.4% and climate 87.1% invalid-payload branches." \
"I2: OQ-4 deadline, recording length and submission constraints remain unanswered and block EPIC-009; reuse blocked P1 TASK-031." \
"I3: The 899 MB backend image ships Streamlit and frontend dependencies; reuse P2 TASK-032." \
"I4: No realistic legacy-schema Firestore history test caught BUG-024; TASK-035 must exercise mixed-vintage records through actual response validation."
```

Closure verification: only STORY-017 changed from in_review to ready, with its sprint assignment cleared. No other existing status changed; neither EPIC-003 nor EPIC-004 auto-closed. CLI closure reported 24/25 sprint-tagged items complete because it includes BUG-023/024; original commitment remains 22/23. The original committed list is unchanged.

## Sprint 4 Recommendation

Capacity baseline is 45 points, the actual completed velocity including 2 unplanned points. Treat it as a ceiling for discussion, not proof that another stretch is sustainable. Recommend a deliberately smaller 19-point core, not padding to consume all 45:

- Process recurrence prevention: TASK-018 (1), TASK-029 (1), TASK-030 (2).
- Production-history and deployment verification: TASK-035 (2), TASK-036 (2).
- Finish the committed analyst outcome: STORY-033 (2), then STORY-017 (3), preserving backend-before-UI dependency order and explicit override provenance.
- Coverage and validation: TEST-001 (1), TASK-033 (1), TASK-034 (1), BUG-006 (1).
- Backend image size: TASK-032 (2).

Suggested goal: Analysts can run a truthful temperature what-if analysis and retrieve mixed-vintage history from a leaner backend, with mandatory live smoke evidence and accurate QA triage.

TASK-031 remains blocked pending OQ-4 human answers; all EPIC-009 stays excluded until then. Existing STORY-029/030/031, EPIC-008/009 work, TASK-015 and deployment/rollback stories remain separate scope, not silently completed or duplicated. Proposed items still need phase-3 grooming and dependency confirmation before any commitment. No sprint 4 was planned.

Phases 9-10 complete. Phase 11 and backlog.py gate were not run. Next action: orchestrator performs sprint 3 sign-off.
