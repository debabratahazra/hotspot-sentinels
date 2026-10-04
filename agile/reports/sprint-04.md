# Sprint 4 Report

Generated 2026-10-03T08:28:08+00:00
Goal: An analyst can run a temperature what-if analysis with clearly labelled caller provenance and review legacy scan history, with the lean backend proven deployable entirely locally.

## Delivery

- Committed: 12 item(s)
- Completed: 12
- Carried over: 0
- Open bugs: 0

| Item      | Type  | Priority | Status | Title                                                                        |
| --------- | ----- | -------- | ------ | ---------------------------------------------------------------------------- |
| STORY-017 | story | P2       | done   | As an analyst I can choose a city, temperature and image and run an analysis |
| BUG-006   | bug   | P2       | done   | Report validator accepts timezone-naive and non-UTC timestamps               |
| TEST-001  | test  | P2       | done   | Raise whole-backend coverage to the 70 percent NFR-9 floor                   |
| TASK-018  | task  | P1       | done   | Verify every acceptance criterion including documentation before handoff     |
| TASK-029  | task  | P1       | done   | Attribute QA failures to owning criteria before blocking committed items     |
| TASK-030  | task  | P1       | done   | Control emergency scope and reserve capacity for recurring retro actions     |
| TASK-032  | task  | P2       | done   | Backend image ships streamlit and the whole frontend dependency tree         |
| STORY-033 | story | P1       | done   | As an analyst I can override the ambient temperature for a what-if analysis  |
| TASK-033  | task  | P1       | done   | Cover uncovered alert payload validation branches                            |
| TASK-034  | task  | P1       | done   | Cover uncovered climate payload validation branches                          |
| TASK-035  | task  | P1       | done   | Exercise realistic legacy Firestore history through API response boundaries  |
| TASK-036  | task  | P1       | done   | Require local-container smoke evidence before validation handoff             |

## Tests

- Result: **PASS**
- Summary: `502 passed, 3 warnings in 54.73s`

## Coverage

- Configuration: `tests/coverage.ini` (backend application code)
- Total: **98.3%**

| File                                 | Covered |
| ------------------------------------ | ------- |
| backend/main.py                      | 96.0%   |
| `backend/services/__init__.py`       | 100.0%  |
| backend/services/alert_dispatcher.py | 100.0%  |
| backend/services/database.py         | 100.0%  |
| backend/services/vision_analyzer.py  | 100.0%  |
| `backend/tools/__init__.py`          | 100.0%  |
| backend/tools/climate_service.py     | 95.2%   |
| backend/tools/seed_samples.py        | 98.9%   |
| backend/verify_setup.py              | 100.0%  |

## Planned versus actual

| Measure                      | Planned / baseline              | Actual                                      |
| ---------------------------- | ------------------------------- | ------------------------------------------- |
| Capacity and delivery        | 19 committed / 21-point ceiling | 19 completed; 2 points remained unallocated |
| Items                        | 12                              | 12 done; zero carry-over                    |
| Passing tests                | 361                             | 502 (+141); 3 warnings                      |
| Backend application coverage | 89.3%                           | 98.3% (+9.0 percentage points)              |
| Backend image                | 899 MB                          | 459 MB (49% smaller)                        |

Velocity is **19 points**, the recommended sprint-5 capacity, not the unused 21-point ceiling or sprint-3 stretch velocity. Capacity discipline held for the first time in three sprints; TASK-030 exists because sprints 2 and 3 both overran.

The coverage change is not a like-for-like test-only improvement. TEST-001 fixed the accounting: tests/coverage.ini explicitly excludes backend/test_analyzer.py and backend/test_pipeline.py, which are ad-hoc manual smoke scripts, uncollected by testpaths and absent from the runtime image. Prior reports needed the footnote "89.3%, or 95.4% excluding the manual scripts"; a figure needing that footnote was not a consistent measurement. No measured backend file is below the 70% floor. Separately supplied QA coverage is 83.3% for frontend/app.py and 78.7% for the canonical validate_report.py; neither belongs in the backend-only 98.3% denominator and neither violates the 70% floor.

## Delivery evidence

The following acceptance evidence was supplied for phases 7-8; this phase-9 invocation independently reran the offline suite and generated the report, not the Docker or cloud checks.

- TASK-032 moved Streamlit into a frontend dependency group. requests correctly remained in core: four backend modules import requests.exceptions.RequestException.
- Local deployability: a clean `docker build -f backend/Dockerfile backend`, followed by a container with `--network=none` and `PORT=8081`, ran as non-root uid 10001. /app contained only main.py, verify_setup.py, services/ and tools/; no Streamlit or uv was shipped.
- Container responses: /api/live 200; /api/health 200 degraded; /api/scans 503 storage_unavailable; text/plain 415; forged JPEG magic bytes 415; 10,000,001 bytes 413; out-of-range temperature 422. Every error used the single `{code, message}` envelope. Deployability evidence required zero cloud spend; it does not claim a new live Cloud Run revision.
- STORY-033 accepts optional finite ambient_temp_c from -50 to 60 degrees C, bypasses telemetry and labels climate_source as caller. STORY-017's sprint-3 partial delivery is closed: the dashboard restored an off-by-default what-if toggle and distinguishes green measured, blue fallback and amber what-if provenance.
- BUG-006 is closed: the canonical validator had accepted naive and non-UTC timestamps for four sprints while supplying sprint acceptance evidence. Z and +00:00 now pass; naive and +08:00 fail identically on Python 3.10 and 3.14.
- TASK-035 provides a negative proof for BUG-024: legacy Firestore records fail the old strict list[AnalysisResponse] model and pass the current model.

## Retrospective

Went well: capacity discipline held; the three twice-deferred retro tasks landed as written rules in .github/copilot-instructions.md; TASK-035 makes the legacy-history regression detectable; the image cut and coverage-accounting correction removed long-standing misleading numbers; full local container evidence cost no cloud quota. Keep these practices; no new item is required for a success.

| Finding                                                                                                                          | Owner    | Decision                                                                                                             |
| -------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------- |
| Documentation drift struck a fourth time; TASK-018 did not prevent the missed Docker instruction surface                         | TASK-037 | P3/new -> P1/ready; add executable acceptance criteria, reuse rather than duplicate                                  |
| Three stale foundation tests and one stale frontend test consumed unplanned restructuring effort                                 | TASK-020 | P2 -> P1; add structural-test impact and reconciliation to pre-plan review                                           |
| Missing uv.lock permission blocked TASK-032 for a full round trip; this was an orchestrator planning error, not an agent failure | TASK-023 | P2 -> P1; require complete write claims before delegation                                                            |
| Legacy manual scripts caused cross-layer, denominator and schema trouble for a third consecutive sprint                          | TASK-038 | New P1, 2 points, blocked on human deletion approval; migrate unique checks first; implementation slice of STORY-022 |
| OQ-4 still blocks the competition's demo/documentation/submission epic                                                           | TASK-031 | Retain P1/blocked; human answers first, no invented deadline                                                         |
| Frontend 83.3% and validator 78.7% coverage need targeted branch follow-up                                                       | TASK-005 | Retain P2/blocked on existing QA dependencies; expand separate coverage accounting and focused checks                |
| Expanded mobile sidebar clipping was observed but remains unverified                                                             | TASK-039 | New P2/ready, 2 points; offline responsive verification and bounded repair                                           |

Every owner above has source=retro, a parent epic and acceptance criteria. No duplicate STORY-029/030/031, TASK-004/015, EPIC-008 or EPIC-009 item was created. TASK-038 is explicitly the retirement implementation slice for STORY-022's existing criterion, not a replacement story or independent duplicate.

### Exact close-sprint arguments

The following is the exact BL command corresponding to the recorded arguments. Execution used the real CLI parser and close handler through a process-local guard that disabled only close_finished_epics. The unguarded handler would mark EPIC-003/004/007 done, contrary to the user's constraint; no CLI source was edited. Do not rerun this command as a sign-off step.

```bash
bl close-sprint \
    --went-well \
    "19/21 points and 12/12 items delivered with zero carry-over: capacity discipline held for the first time in three sprints; retain TASK-030." \
    "The three twice-deferred retro tasks landed as written verification rules; retain independent evidence and TASK-035 negative proof against the old strict history model." \
    "Backend image 899 MB to 459 MB (49% smaller), honest coverage accounting 89.3% to 98.3%, and complete local container deployability evidence at zero cloud cost." \
    --improve \
    "OQ-4 still blocks all EPIC-009; TASK-031 must obtain human competition constraints before demo, documentation and submission can become the priority." \
    "Frontend coverage 83.3% and canonical validator coverage 78.7% remain weaker than the backend; TASK-005 owns focused branch follow-up and explicit separate accounting." \
    "Mobile layout was observed clipping with the sidebar expanded and remains unverified; add a tracked responsive verification task under EPIC-007." \
    --went-wrong \
    "Documentation drift struck a fourth time: docker-cloudrun instructions still prescribe the root build context abandoned by TASK-025 in sprint 3, despite README and deploy skill updates; TASK-037, not another twin. TASK-018 did not prevent this recurrence." \
    "Three stale foundation tests and one stale frontend test required mid-sprint rewrites for deliberately changed structures; predictable restructuring impact kept consuming unplanned effort. TASK-020 must identify affected assertions before commitment." \
    "TASK-032 hit a hard blocker because uv.lock was omitted from the permitted file list, costing a full round trip. This was an orchestrator planning error, not an agent failure; TASK-023 must include complete write claims in delegation planning." \
    "The two legacy manual scripts caused cross-layer, coverage-denominator and schema trouble for a third consecutive sprint; add an approval-blocked retirement task after migrating unique checks into opt-in smoke verification."
```

Close verification: all 12 committed items remain done, completed points are 19, carry-over is empty, returned-to-ready is empty, and every pre-existing item status was unchanged by close. Epic auto-completion was not performed. No new sprint was planned.

## Final backlog statistics

```json
{
    "current_sprint": 4,
    "total": 106,
    "open": 35,
    "open_bugs": 0,
    "by_status": {"groomed": 16, "ready": 2, "done": 69, "blocked": 19},
    "by_type": {"epic": 9, "story": 33, "task": 39, "bug": 24, "test": 1},
    "loop_done": false
}
```

## Sprint 5 recommendation, not a commitment

Capacity: **19 points**. Proposed goal: **A judge can understand the delivered system and rehearse a truthful competition demo against agreed submission requirements.**

The core is close enough that unblocking EPIC-009 should now be the priority; optional coverage polish should not displace competition delivery. The project is not complete: OQ-4, identity/provenance agreement, retained-imagery work and genuine live-deployment/IAM evidence remain unresolved. Existing TASK-004/015 and STORY-029/030/031 retain their actual states and must not be silently treated as satisfied.

Immediately available offline candidates: TASK-037 (1), TASK-020 (1), TASK-023 (1), TASK-039 (2), totaling 5 points; process tasks still require normal grooming. Seek TASK-031's human answers (1) before planning submission work. Conditional candidates in dependency order: STORY-030 (2), STORY-029 (3), STORY-031 (3), STORY-026 (2), STORY-027 (2). With the offline candidates and TASK-031 this is an 18-point upper-bound candidate set, not a dependency-closed commitment: STORY-026/027 require their existing deployment/artifact prerequisites and explicit quota authorization. If those remain unavailable, leave capacity unused rather than fill it with unrelated work. TASK-038 (2) is an optional equal-point swap only after human deletion approval; STORY-028/032 and TASK-006 remain subsequent delivery candidates with their own dependencies, not hidden work.

STOP after phase 10. Phase 11, bl gate and all gcloud commands were intentionally not run. No production code, tests or protected .github/docs/ files were edited; no item was marked done. Single next action: the orchestrator performs sprint-4 sign-off and requests the OQ-4 human decision before authorizing sprint-5 planning.
