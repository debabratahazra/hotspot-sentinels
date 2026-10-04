# Sprint 4: Grooming and Planning Complete

## Decision Table

Every status or priority change is recorded below, including intermediate ready states. Estimates are unchanged. No item was marked done.

| Item      | Old state  | New state / transition               | Why                                                                                                      |
| --------- | ---------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| TASK-018  | groomed/P1 | ready/P1 -> in_sprint/P1             | Recurring criterion/documentation handoff drift; reserve prevention before implementation.               |
| TASK-029  | groomed/P1 | ready/P1 -> in_sprint/P1             | Wrong QA attribution recurred twice; establish owning-criterion triage.                                  |
| TASK-030  | groomed/P1 | ready/P1 -> in_sprint/P1             | Capacity discipline broke twice; preserve original versus emergency commitments.                         |
| STORY-033 | new/P1     | ready/P1 -> in_sprint/P1             | Backend prerequisite for the unmet temperature control; local contract evidence.                         |
| TASK-033  | new/P2     | ready/P2 -> ready/P1 -> in_sprint/P1 | Invalid-alert-payload prevention must sort before its TEST-001 accounting consumer.                      |
| TASK-034  | new/P2     | ready/P2 -> ready/P1 -> in_sprint/P1 | Invalid-telemetry-payload prevention must sort before its TEST-001 accounting consumer.                  |
| TASK-035  | new/P1     | ready/P1 -> in_sprint/P1             | Prevent recurrence of BUG-024 using actual response models and legacy-shaped offline history.            |
| TASK-036  | new/P1     | ready/P1 -> in_sprint/P1             | Replace live-deploy handoff criteria with mandatory local-container smoke evidence.                      |
| STORY-017 | ready/P1   | ready/P2 -> in_sprint/P2             | Its newer P1 API prerequisite STORY-033 must sort first; partial slider criterion retained.              |
| BUG-006   | groomed/P2 | ready/P2 -> in_sprint/P2             | Local UTC validator correction with regression evidence.                                                 |
| TEST-001  | groomed/P2 | ready/P2 -> in_sprint/P2             | Own honest denominator accounting and cover-or-retire disposition, not duplicate branch tests.           |
| TASK-032  | new/P2     | ready/P2 -> in_sprint/P2             | Lean backend manifest/image verified locally; P2 retained, not dependent on deployment.                  |
| STORY-014 | blocked/P2 | groomed/P2                           | All named prerequisites shipped; defer overlapping image acceptance, do not infer completion.            |
| STORY-031 | blocked/P2 | groomed/P2                           | STORY-010/006 shipped; explicit sprint exclusion remains, and actual GCS acceptance is not demonstrated. |
| TASK-004  | groomed/P2 | blocked/P2                           | Actual runtime IAM evidence requires prohibited live cloud work.                                         |

Additional metadata-only changes: explicit file claims for all twelve committed items; STORY-033 now owns only API work, and STORY-017 owns the original slider-through-analyzer integration criterion. The caller-temperature provenance value is `caller`, distinct from `bigquery` and `fallback`. TASK-033/034 are test-only, with production modules read-only. TASK-035 corrects traceability to FR-18/24. TASK-030 criteria recognize already-shipped TASK-016/017/021 instead of recommitting them. TASK-036 is renamed to local-container smoke, with an explicit offline mode required. STORY-014's obsolete root build context is reconciled to `backend/`. Remaining stale blocker descriptions are refreshed below. No protected `.github/docs/` file was edited.

## Capacity and Goal

Capacity is **21 points**, with **19 committed and 2 deliberately unallocated**. This is a ceiling, not a target to fill. Sprint 3's human-authorized capacity was 46, with 43 original points completed plus 2 unplanned points = 45 actual delivery; that stretch is not a sustainable baseline. The smaller observed sprint-2 delivery of 21 provides a conservative ceiling relative to 45, but it also included 6 emergency points over its original 15-point plan. Accordingly, 21 is not presented as proven normal velocity: only 19 points are committed, discretionary backlog is not pulled into the two-point gap, and 4 committed points are reserved for TASK-018/029/030 process prevention. The 2-point smoke-prevention task is additional. Any emergency intake needs an explicit authorized rebaseline or equal-point swap; the gap is not automatic authorization.

The twelve recommended items total **19 points** in the real backlog. All IDs and estimates match; the priority changes above address actual planner ordering, not new estimates or invented stories.

Sprint goal: **An analyst can run a temperature what-if analysis with clearly labelled caller provenance and review legacy scan history, with the lean backend proven deployable entirely locally.**

## Governing Quota Constraint

- No Cloud Run deploy, image push, traffic change, IAM mutation, or other cloud resource expenditure in sprint 4.
- No live Gemini, BigQuery, Firestore, Pub/Sub or GCS work in development or verification. All cloud boundaries use credential-free mocks; actual cloud acceptance remains unverified, not passed.
- Phase 7 is local deployability: `docker build -f backend/Dockerfile backend`, run the final image, and smoke-test the actual local container. These commands are future acceptance steps; none was run during planning.
- The existing pipeline smoke default invokes live Vertex and writes real Firestore/Pub/Sub data. It is prohibited in this sprint. TASK-036 must provide an explicit offline-container path before it can be used, without invoking doctor/live connectivity/upload steps or mounting ADC or `.env`. Cloud access must fail closed while local HTTP remains usable.
- Container evidence must record source revision, image ID/digest, build/run commands, local URL, health/liveness, schema-valid analysis including caller temperature, current plus legacy-shaped persisted offline history, and HTTP 415 upload rejection. Failures block the validation handoff and receive correctly parented defects.
- The existing live revision `hotspot-backend-00003-vfh` is supplied sprint-3 evidence; it is not reverified or redeployed here. Supplied baseline: 361 passing tests and 89.3% backend coverage. Neither is remeasured in phases 3-4.

## Verified Ready Queue and Exact Plan Output

Before planning, the only ready records were the twelve below, in this exact `(priority, created)` order, totaling 19 points. No new records remained. All nine epic containers were groomed with no sprint assignment. The first queue check caught TEST-001 sorting before its branch inputs; promoting TASK-033/034 fixed it, and the identical check passed before planning.

Command:

```bash
bl plan --capacity 21 --goal "An analyst can run a temperature what-if analysis with clearly labelled caller provenance and review legacy scan history, with the lean backend proven deployable entirely locally."
```

Exact output, with terminal display wrapping removed:

```text
Sprint 4 planned — 12 item(s), 19/21 points
  TASK-018   P1 (1) Verify every acceptance criterion including documentation before handoff
  TASK-029   P1 (1) Attribute QA failures to owning criteria before blocking committed items
  TASK-030   P1 (2) Control emergency scope and reserve capacity for recurring retro actions
  STORY-033  P1 (2) As an analyst I can override the ambient temperature for a what-if analysis
  TASK-033   P1 (1) Cover uncovered alert payload validation branches
  TASK-034   P1 (1) Cover uncovered climate payload validation branches
  TASK-035   P1 (2) Exercise realistic legacy Firestore history through API response boundaries
  TASK-036   P1 (2) Require local-container smoke evidence before validation handoff
  STORY-017  P2 (3) As an analyst I can choose a city, temperature and image and run an analysis
  BUG-006    P2 (1) Report validator accepts timezone-naive and non-UTC timestamps
  TEST-001   P2 (1) Raise whole-backend coverage to the 70 percent NFR-9 floor
  TASK-032   P2 (2) Backend image ships streamlit and the whole frontend dependency tree
```

Every listed record is now `in_sprint`, sprint 4; the ready queue is empty. No Phase 5 status was entered.

## Blocker Review

All nineteen previously blocked records were reviewed. Clearing one shipped prerequisite does not clear an item's remaining unbuilt dependency or human decision.

| Item      | Shipped/stale blockers cleared                                     | Remaining disposition                                                                         |
| --------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| STORY-014 | STORY-010, STORY-013, TASK-025; all other named prerequisites done | groomed, deferred; no independent completion claim.                                           |
| STORY-015 | None newly shipped among STORY-014/TASK-004                        | blocked: both uncommitted and live deployment prohibited.                                     |
| STORY-016 | STORY-010                                                          | blocked: STORY-015 uncommitted; cloud rollback evidence prohibited.                           |
| STORY-023 | STORY-003, STORY-005, STORY-007                                    | blocked: STORY-022 uncommitted and STORY-030 provenance contract unagreed.                    |
| STORY-024 | STORY-010, STORY-011, STORY-012, STORY-013                         | blocked: STORY-022 and STORY-029 uncommitted.                                                 |
| STORY-025 | STORY-001 already done                                             | blocked: STORY-022 and STORY-030 uncommitted.                                                 |
| TASK-005  | None among STORY-023/024/025                                       | blocked: broad QA prerequisites uncommitted.                                                  |
| STORY-026 | Foundation tasks already done                                      | blocked: STORY-015 and OQ-4; all EPIC-009 excluded.                                           |
| STORY-027 | STORY-010, STORY-008                                               | blocked: STORY-031 and OQ-4; all EPIC-009 excluded.                                           |
| STORY-028 | STORY-020, STORY-021                                               | blocked: STORY-016/026, partial STORY-017 and OQ-4; all EPIC-009 excluded.                    |
| TASK-006  | None sufficient to unblock submission                              | blocked: STORY-016/028/026/027, TASK-005 and OQ-4.                                            |
| STORY-029 | STORY-001 already done                                             | blocked: STORY-030's unagreed serialized identity provenance; explicitly excluded.            |
| STORY-030 | STORY-001 already done                                             | blocked: product-owner/contract-auditor agreement still absent; no identity fields invented.  |
| STORY-031 | STORY-010; STORY-006 already done                                  | groomed, explicitly deferred; real GCS object evidence not permitted.                         |
| STORY-032 | STORY-011 and ratified OQ-2 byte limit                             | blocked: STORY-029 and OQ-4; all EPIC-009 excluded.                                           |
| TASK-011  | None                                                               | blocked: human owns protected documentation edits.                                            |
| TASK-015  | Live revision does not prove its three specific criteria           | blocked: human provisioning, GCS sample upload and real Vertex evidence; explicitly excluded. |
| TASK-022  | None                                                               | blocked: human-approved editor/template-access policy required.                               |
| TASK-031  | OQ-2/OQ-5 were already resolved in its current record              | blocked: OQ-4 deadline, recording length and submission/sharing forms remain unanswered.      |

TASK-004 is additionally blocked in this grooming pass because its actual IAM acceptance evidence is live-cloud work.

## Dependency Closure

Executable assertions passed after grooming and immediately after `bl plan`:

- STORY-033 depends on done STORY-010 and TASK-026/027/028.
- TASK-035 depends on STORY-033 committed earlier, plus done BUG-024/TASK-026.
- STORY-017 depends on STORY-033 committed earlier, plus done STORY-018/019/020/021.
- TEST-001 depends on TASK-033/034 committed earlier. Broad EPIC-008 stories are accounting context, not hidden prerequisites.
- TASK-036 establishes the smoke process; STORY-016 is future rollback ownership, not its prerequisite. Final smoke execution waits for all sprint changes and QA.
- Other committed items have no unfinished declared prerequisites. No committed item depends on uncommitted unfinished work. Parent epics are containers, not executable prerequisites.
- All nine epics remain groomed and unassigned; no epic was ready or committed. The 57 done records and all estimates remain unchanged.

## File-Grouped Build Order

One subagent per item. An item holds its entire file set atomically, not one agent per table row. Arrows below are separate, sequential invocations. Shared helpers, instruction files, manifests and evidence outputs are locks too.

| File / exact ownership boundary                                                                                                                                                                                                       | Ordered item owners                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `.github/agents/product-owner.agent.md`, `.github/agents/story-builder.agent.md`                                                                                                                                                      | TASK-018                                                                                      |
| `.github/agents/qa-engineer.agent.md`                                                                                                                                                                                                 | TASK-029                                                                                      |
| `.github/agents/scrum-master.agent.md`                                                                                                                                                                                                | TASK-030                                                                                      |
| `tests/test_sprint4_process.py` (planned new process regression module)                                                                                                                                                               | TASK-018 -> TASK-029 -> TASK-030                                                              |
| `agile/requirements.md`                                                                                                                                                                                                               | TASK-018 -> STORY-033                                                                         |
| `.github/skills/agile-sdlc-loop/scripts/sprint_report.py`                                                                                                                                                                             | TASK-030 -> TEST-001                                                                          |
| `backend/main.py`, `COPILOT_GUIDE.md`                                                                                                                                                                                                 | STORY-033                                                                                     |
| `tests/test_api.py`, `tests/test_cross_layer_contract.py`                                                                                                                                                                             | STORY-033 -> TASK-035                                                                         |
| `frontend/app.py`, `frontend/.streamlit/config.toml`, `tests/test_frontend.py`                                                                                                                                                        | STORY-017; must wait for STORY-033                                                            |
| `tests/test_alert_dispatcher.py`                                                                                                                                                                                                      | TASK-033; test-only, `backend/services/alert_dispatcher.py` read-only                         |
| `tests/test_climate_service.py`                                                                                                                                                                                                       | TASK-034; test-only, `backend/tools/climate_service.py` read-only                             |
| `.github/skills/heat-report-validation/scripts/validate_report.py`, `tests/test_contract.py`                                                                                                                                          | BUG-006                                                                                       |
| `.github/skills/agile-sdlc-loop/references/phases.md`, `.github/skills/pipeline-smoke-test/SKILL.md`, `.github/skills/pipeline-smoke-test/scripts/smoke_test.sh`, `tests/test_sprint4_smoke.py` (planned new smoke regression module) | TASK-036                                                                                      |
| `pyproject.toml`, `README.md`, `tests/test_sprint_packaging.py`                                                                                                                                                                       | TASK-032 -> TEST-001                                                                          |
| `uv.lock`, `backend/requirements.txt`, `requirements.txt`, `tests/test_package_layout.py`                                                                                                                                             | TASK-032                                                                                      |
| `backend/test_analyzer.py`, `backend/test_pipeline.py`                                                                                                                                                                                | TEST-001; document cover-or-retire decision with product-owner/QA, never execute live scripts |

TASK-035 is test-only: its only writable files are the two named API/contract test modules. TASK-033/034 are also test-only, not permission to repair production code. Tests for STORY-017's through-analyzer integration belong to `tests/test_frontend.py`; they may consume the API read-only, but cannot also write `tests/test_api.py` while TASK-035 owns it. Shared `tests/conftest.py` and unlisted fixtures/helpers are read-only in all concurrent waves. If a new shared write is necessary, stop and serialize or amend the file claims before dispatch. No unlisted shared helper may be created by competing agents.

## Wave Plan

| Wave             | Dispatch                                                            | Wait / contention rule                                                                                                                                                                                                                                                                                             |
| ---------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0                | TASK-018 -> TASK-029 -> TASK-030 -> TASK-036, one at a time         | Establish criterion, triage, capacity and offline-smoke procedures first. The first three share `tests/test_sprint4_process.py`; TASK-018 owns requirements before STORY-033; TASK-030 owns reporting before TEST-001. TASK-036's final container evidence is collected later, not claimed at this stage.          |
| 1                | STORY-033, TASK-033, TASK-034 and BUG-006 may run concurrently      | Exact declared file sets are disjoint, including test modules. No shared fixture writes, dependency/environment changes, whole-suite runs or global coverage/evidence writes while producers are active. Each agent's narrow checks must have isolated outputs. Wait for all four handoffs and integration checks. |
| 2                | TASK-035 and STORY-017 may run concurrently                         | Both wait for accepted STORY-033. TASK-035 alone owns API/cross-layer tests; STORY-017 alone owns frontend/test_frontend. Preserve read-only shared fixtures and backend for the frontend integration proof. Wait for both handoffs.                                                                               |
| 3                | TASK-032 alone                                                      | Dependency manifests, lockfile, README, package-layout and packaging tests are global environment-sensitive writes. No other agent installs, rewrites manifests or produces coverage concurrently. Verify the actual workspace export and eventual local image, not a temporary copy.                              |
| 4                | TEST-001 alone                                                      | Wait for branch work and packaging so denominator/reporting reflect the final source scope. Do not hide the two legacy scripts to inflate the official total. Report comparable total/delta and any approved retirement explicitly.                                                                                |
| Later acceptance | QA/contract checks, then final local-container smoke under TASK-036 | Serialized after all changes: final-image build/run and smoke prove local deployability. No cloud deploy, cloud calls, or rollback. This is future phase-6/7/8 work, not performed in this planning request.                                                                                                       |

Priority order is the valid dependency-ordered commitment queue; independent lanes need not idle solely to reproduce queue order. Cross-file items are never split into separate writers. QA's whole-suite/coverage/report/evidence writers run only when producer agents are idle, not concurrently with them.

## Deferred List

All nine epics remain groomed containers. Twenty-five unfinished executable items remain outside sprint 4:

- Explicit exclusions/human/live-cloud scope: STORY-015/016/029/030/031; TASK-004/015/031; all EPIC-009 children STORY-026/027/028/032 and TASK-006. OQ-4 also keeps EPIC-009 out; no deploy-dependent item is committed.
- Overlapping image acceptance: STORY-014, now groomed; TASK-032/TASK-036 own this sprint's lean-image and local-smoke work. Do not mark STORY-014 done by assumption.
- Broad QA and reporting stories: STORY-022/023/024/025, TASK-005. Narrow prevention is committed; these are not hidden dependencies of it. STORY-022's retirement criterion remains uncompleted even if TEST-001 documents its disposition.
- Other lower-priority process/configuration work: TASK-014/019/020/023 (groomed), TASK-011/022 (human-blocked). TASK-014 may be edited locally in a future sprint, but cloud provisioning evidence is not authorized here. TASK-019's wider caller-identity checks remain relevant to deferred STORY-029/030; TASK-020/023 are existing complements, not duplicates of TASK-030.

The unallocated two points do not authorize pulling any deferred item into sprint 4.

## Final bl stats

```json
{
  "current_sprint": 4,
  "total": 103,
  "open": 46,
  "open_bugs": 1,
  "by_status": {
    "groomed": 16,
    "in_sprint": 12,
    "done": 57,
    "blocked": 18
  },
  "by_type": {
    "epic": 9,
    "story": 33,
    "task": 36,
    "bug": 24,
    "test": 1
  },
  "loop_done": false
}
```

STOP at Phase 4. No production code, tests, agent instructions or smoke procedures were implemented; only backlog metadata and this planning document changed. No gcloud or Docker command was executed. Single next action: on a fresh Phase 5 instruction, dispatch TASK-018 alone with its complete file claims and the local-only constraint.
