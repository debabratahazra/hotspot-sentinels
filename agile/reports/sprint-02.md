# Sprint 2 Report

Generated 2026-10-02T19:35:22+00:00
Goal: An analyst can submit an aerial image, receive a valid heat report grounded in labelled climate data, review persisted scans, and see truthful critical-alert status without the current coroutine, schema, SQL-injection or credential-packaging failures.

## Delivery

- Committed: 14 item(s)
- Completed: 14
- Carried over: 0
- Open bugs: 2

| Item      | Type  | Priority | Status | Title                                                                     |
| --------- | ----- | -------- | ------ | ------------------------------------------------------------------------- |
| STORY-004 | story | P1       | done   | As an analyst my zone score is grounded in a real ambient temperature     |
| STORY-006 | story | P1       | done   | As an analyst I can see my previous scans                                 |
| BUG-007   | bug   | P0       | done   | /api/analyze never awaits the async analyzer, returning a coroutine       |
| BUG-008   | bug   | P0       | done   | Critical alerts never fire because main.py reads a deleted schema field   |
| BUG-009   | bug   | P1       | done   | CORS allows every origin instead of reading ALLOWED_ORIGINS               |
| BUG-010   | bug   | P0       | done   | BigQuery climate query interpolates station_id into SQL                   |
| TASK-024  | task  | P1       | done   | Remove the duplicate backend/requirements.txt manifest                    |
| BUG-011   | bug   | P0       | done   | No .dockerignore, so COPY . . can bake .env and .venv into the image      |
| BUG-012   | bug   | P0       | done   | Dashboard reads schema fields that no longer exist                        |
| BUG-013   | bug   | P0       | done   | Dashboard hardcodes the deployed Cloud Run URL with no timeout            |
| BUG-014   | bug   | P0       | done   | Pub/Sub client construction sits outside the dispatcher's failure handler |
| BUG-015   | bug   | P0       | done   | API accepts a non-image upload and spends Gemini budget on it             |
| BUG-016   | bug   | P0       | done   | API accepts an unbounded upload with no size limit                        |
| BUG-017   | bug   | P0       | done   | Pub/Sub publish failures disclose raw cloud payloads in stdout logs       |

## Tests

- Result: **PASS**
- Summary: **208 passed**, 0 failures, 0 errors, 0 skipped (fresh JUnit evidence).

## Coverage

- Total: **90.9%**

| File                                 | Covered |
| ------------------------------------ | ------- |
| backend/main.py                      | 100.0%  |
| `backend/services/__init__.py`       | 100.0%  |
| backend/services/alert_dispatcher.py | 100.0%  |
| backend/services/database.py         | 100.0%  |
| backend/services/vision_analyzer.py  | 100.0%  |
| backend/test_analyzer.py             | 0.0%    |
| backend/test_pipeline.py             | 0.0%    |
| `backend/tools/__init__.py`          | 100.0%  |
| backend/tools/climate_service.py     | 93.0%   |
| backend/tools/seed_samples.py        | 98.9%   |
| backend/verify_setup.py              | 100.0%  |

Below the 70% floor — needs test tasks next sprint:

- backend/test_analyzer.py
- backend/test_pipeline.py

## Open bugs carried forward

- BUG-006 (P2) Report validator accepts timezone-naive and non-UTC timestamps
- BUG-019 (P1) Missing-project SDK failure bypasses every degradation policy

## Scope and outcome reconciliation

- Original plan: **9 items / 15 points**, preserved in sprint-02-planning.md.
- Expanded commitment and actual delivery: **14/14 items / 21 points**; no carry-over.
- Actual velocity is **21 points**, including **5 unplanned emergency items / 6 points**. The sprint was deliberately expanded for live security exposures; 21 is not evidence of a stable 21-point planned throughput.
- Passing tests increased **82 -> 208** (+126); whole-backend coverage increased **61.7% -> 90.9%** (+29.2 percentage points).
- Previously uncovered main.py, database.py, alert_dispatcher.py and climate_service.py now have 100%, 100%, 100% and 93% coverage respectively.
- The goal is met in the repository. The serving Cloud Run revision still runs pre-sprint-2 code, including the coroutine bug; live deployment and acceptance remain human-unconfirmed under TASK-013/TASK-015.
- The gate passed according to the supplied evidence. Phase 11 and the gate were **not rerun** here; sign-off belongs to the orchestrator.
- Closure verified all 14 commitments remained done, zero items returned to ready, and the total done count stayed 30. BUG-018 remains done outside the recorded commitment and is not added to the 21-point velocity.
- Two legacy manual scripts remain below the 70% per-file floor: backend/test_analyzer.py and backend/test_pipeline.py, both 0%. Reuse STORY-022/TEST-001 for QA disposition rather than inventing duplicate coverage work; no completion status changed.

## Retrospective findings to items

All converted corrective items carry source=retro. Original audit provenance is retained in reused item descriptions. New tasks have explicit acceptance criteria, parent epics and requirement traces; they remain new pending grooming, not committed to sprint 3.

| Finding                                                                                        | Corrective item or retained practice                                                                                                                                           |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| W1: Coverage 61.7% -> 90.9%; 208 versus 82 passing                                             | Keep scoped mocked success/failure coverage; TEST-001 remains available for QA disposition. No new item.                                                                       |
| W2: Independent audit caught F1 and F5 despite green tests, second sprint running              | Keep the read-only Phase 8 audit; BUG-019 is tracked and BUG-018 is already fixed/done. No new item.                                                                           |
| W3: Full stories across nine epics exposed eight stale blockers                                | Keep full story-set and prerequisite review before grooming. No item.                                                                                                          |
| W4: SQL injection, public wildcard CORS and credential-packaging defects closed                | Keep query binding, explicit origins and effective build-context exclusions; BUG-010/009/011 remain done. No item.                                                             |
| R1: Async/schema producer change broke API, alerts and dashboard for a sprint and was deployed | **TASK-028 (new, P1, 3 points)**: standing same-change pre-merge/pre-deploy cross-layer compatibility gate; **TASK-026 (existing)**: HTTP response model.                      |
| R2: QA blocked wrong committed items and mis-parented three P0 bugs                            | **TASK-029 (new, P1, 1 point)**: criterion/owner/commitment-based triage before blocking; reuse STORY-007/011 and existing defects.                                            |
| R3: Canonical workspace verification nearly replaced by a copy again                           | **TASK-016 (existing, P2 -> P1)**: blocking canonical-path/working-directory evidence; recurrence noted.                                                                       |
| R4: Narrow exception tuples missed SDK/base failures for the third time                        | **TASK-017 (existing, P2 -> P1)**: enforced construction/operation failure matrix; **BUG-019 (existing, P1)**: actual missing-project repair.                                  |
| R5: Backend MIME fix exposed dashboard hardcoded JPEG                                          | **TASK-028**: PNG/JPEG dashboard-to-API-to-analyzer regression gate; **BUG-018** remains done, no duplicate.                                                                   |
| R6: Deliberate 15 -> 21 emergency expansion broke capacity discipline                          | **TASK-030 (new, P1, 2 points)**: original-plan accounting, explicit emergency rebaseline or equal-point swaps; complements TASK-020/023.                                      |
| I1: Live revision still pre-sprint-2; deployment unconfirmed                                   | **TASK-013/015 (existing, P2 -> P1, still blocked)**: human-authorized repaired deploy and live evidence; **TASK-025 (existing, P2 -> P1)**: prerequisite container hardening. |
| I2: TASK-016/017/021 unscheduled and classes recurred                                          | **TASK-016/017/021 (existing, P2 -> P1)**, plus **TASK-030** to reserve recurrence-prevention capacity. No duplicate prevention tasks.                                         |
| I3: OQ-2 decimal limit lacks human ratification; OQ-4/5 block grooming                         | **TASK-031 (new, P1, 1 point)**: human answers through product owner; affected stories stay blocked pending confirmation. TASK-011 remains human-owned protected-doc work.     |
| I4: climate_source and US BigQuery exception undocumented                                      | **TASK-027 (existing, P2 -> P1, 1 point)**: documentation before dependent TASK-026 acceptance.                                                                                |

## Exact close command

The shell helper was defined as `bl() { python3 .github/skills/agile-sdlc-loop/scripts/backlog.py "$@"; }`.

```bash
bl close-sprint \
--went-well "W1: Coverage 61.7% -> 90.9% (+29.2pp); main/database/alerts now 100%, climate 93%; 208 passing versus 82. W2: Independent Phase 8 audit caught F1/OSError and F5/PNG MIME despite 208 passing tests, for a second sprint. W3: Full stories for nine epics exposed eight stale blockers whose prerequisites shipped. W4: SQL injection, wildcard public CORS and credential-packaging exposures were closed in the repository." \
--improve "I1: Live Cloud Run still runs pre-sprint-2 code; TASK-013 and human deployment remain unconfirmed. I2: TASK-016/017/021 were never scheduled and their defect classes recurred; reserve capacity for recurrence prevention. I3: OQ-2 upload limit was ruled 10,000,000 bytes by orchestrator, not human; OQ-4/5 block EPIC-005/007/009 grooming. I4: climate_source and BIGQUERY_LOCATION=US remain undocumented in guide sections 3/2; TASK-027." \
--went-wrong "R1: STORY-001 async/schema change excluded API/dashboard consumers; coroutine BUG-007, dead alerts BUG-008 and None-temperature BUG-012 persisted a whole sprint and were deployed; five P0 defects from one uncoordinated change. R2: QA held BUG-007/008 over uncommitted STORY-011/007 criteria and assigned three P0 bugs to wrong parents; orchestrator corrected attribution. R3: Temp-copy verification nearly repeated sprint-1 BUG-004; TASK-016 still unactioned. R4: Narrow exception tuples missed DataCorruption, then RpcError/TimeoutError/MessageTooLargeError, then OSError/EnvironmentError (BUG-005/014/019); TASK-017 exists but is unenforced. R5: BUG-015 MIME forwarding exposed the dashboard's hardcoded JPEG, causing BUG-018; cross-layer impact was unchecked. R6: Deliberate emergency expansion from 9 items/15 points to 14/21 addressed live security exposures but broke capacity discipline; 21 is actual velocity including 6 unplanned points. Goal met in repository, not verified on live revision; gate passed per supplied evidence, not rerun."
```

## Final backlog stats

```json
{"current_sprint":2,"total":92,"open":62,"open_bugs":2,"by_status":{"new":7,"groomed":9,"ready":18,"done":30,"blocked":28},"by_type":{"epic":9,"story":32,"task":31,"bug":19,"test":1},"loop_done":false}
```

## Sprint 3 recommendation only

Capacity ceiling: **21 points**, based on actual completed velocity, with the emergency-scope caveat above. No sprint was planned or item committed.

Suggested goal: make the repaired analysis pipeline safe to change and demonstrate its behavior on the serving Cloud Run revision.

- Recurrence prevention: TASK-016/017/021 (1 each), TASK-028 (3), TASK-029 (1), TASK-030 (2): **9 points**.
- Contract and failure repairs: BUG-019 (2), TASK-027 (1), TASK-026 (2), BUG-006 (1): **6 points**.
- Deployment preparation and decisions: TASK-025 (2), TASK-031 (1), STORY-013 history acceptance (1): **4 points**.
- Human-conditional live work: TASK-015 (1), TASK-013 (1): **2 points**. Keep blocked unless human authorization and provisioning evidence are secured before commitment; otherwise recommend **19 points**, not a fictional dependency-closed 21.
- Sequence BUG-019, TASK-025 and live provisioning before deployment; TASK-027 precedes TASK-026 acceptance. Existing completed service prerequisites are satisfied. New items need grooming; broad STORY-007/011 and unresolved product scope are not smuggled into narrow fixes.

Next action: hand this closed sprint and report to the orchestrator for Phase 11 sign-off. Do not start sprint 3 here.
