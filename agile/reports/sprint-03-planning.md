# Sprint 3: Phase 4 Complete

Planning completed on 2026-10-03 after the human accepted grooming and supplied five rulings. This section is authoritative; the earlier conditional report is retained below as superseded history. Phase 5 has not started. No production code, tests, or protected .github/docs/ were changed; no item was marked done.

## Applied Decisions

All 23 selected items transitioned from ready to in_sprint through bl plan. The table records the preceding ruling changes, relative to the accepted grooming state; unchanged priorities are explicit.

| Item                                       | Accepted grooming state | Pre-plan state | Why                                                                                                                                                                                                      |
| ------------------------------------------ | ----------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-029, STORY-030                       | blocked/P1              | blocked/P1     | Deferred to sprint 4; STORY-029 now names STORY-030 and the unagreed serialized per-field provenance shape.                                                                                              |
| STORY-003                                  | groomed/P2              | ready/P1       | Include the 2-point HVI prerequisite before STORY-010 and STORY-018.                                                                                                                                     |
| STORY-009                                  | blocked/P2              | ready/P2       | Human ratifies readiness timeout of 5 s; service dependencies selected.                                                                                                                                  |
| STORY-010                                  | blocked/P2              | ready/P2       | Human ratifies -50 to 60 degrees C inclusive; STORY-003 included, STORY-029 removed as a sprint-3 prerequisite.                                                                                          |
| STORY-011                                  | blocked/P1              | ready/P1       | Human ratifies MAX_UPLOAD_BYTES = 10,000,000 decimal bytes, not 2^23.                                                                                                                                    |
| STORY-017, STORY-018, STORY-019, STORY-020 | blocked/P3              | ready/P3       | Selected API/service/rubric prerequisites resolve same-sprint sequencing; STORY-029 removed from STORY-017.                                                                                              |
| STORY-021                                  | blocked/P3              | ready/P3       | Human ratifies REQUEST_TIMEOUT_SECONDS: 5 s connect, 60 s read.                                                                                                                                          |
| TASK-013                                   | blocked/P3              | ready/P3       | End-of-sprint deployment authorized; TASK-025 hard predecessor; TASK-015 removed. Deploy plus passing live /api/health supplies needed provisioning evidence, not completion of all deployment criteria. |
| TASK-016, TASK-021                         | ready/P1                | ready/P0       | Establish recurrence-prevention handoff gates before implementation.                                                                                                                                     |
| TASK-017, BUG-019, TASK-028                | ready/P0                | ready/P0       | Keep exception prevention before repair and compatibility gate before contract-touching stories.                                                                                                         |
| TASK-031                                   | blocked/P1              | blocked/P1     | Narrow description and criteria to OQ-4 only: deadline, recording length and submission/sharing form; EPIC-009 deferred.                                                                                 |
| TASK-015                                   | blocked/P1              | blocked/P1     | Deferred; description no longer presents this as a TASK-013 prerequisite. Provisioning script, GCS samples and real Vertex evidence remain unproved.                                                     |

Additional active dependencies were recorded explicitly: TASK-017 before BUG-019; TASK-016/017/021 before TASK-028; TASK-028 before affected stories; BUG-019 before climate/error/history acceptance; STORY-010 and TASK-027 before TASK-026; TASK-026 before STORY-017; and accepted dashboard work before final TASK-013. Estimates, creation timestamps, done states and epic containers were not changed.

## Capacity and Goal

Human-authorized capacity: 46 points. Sprint 2 demonstrated velocity: 21 points. This is a deliberate stretch of 25 points, not a revised historical velocity or evidence of increased delivery capacity. No commitment exceeds the authorized 46 points.

Goal: An analyst can upload an aerial image in the dashboard, receive a rubric-consistent heat report with labelled climate data, persisted history and truthful alert status, and use the repaired service deployed from a hardened image.

## Verified Ready Queue and Commitment

The exact pre-plan ready queue was 23 items / 46 points, with no extra ready records. The following output gives its verified priority, points and order; after planning every listed record is in_sprint with sprint=3, and ready=0. Area totals match the human proposal exactly: prevention/defect 8, rubric 2, climate 2, alerts 4, API 15, dashboard 12, shipping 3. No estimate reconciliation was needed.

Command:

```bash
bl plan --capacity 46 --goal "An analyst can upload an aerial image in the dashboard, receive a rubric-consistent heat report with labelled climate data, persisted history and truthful alert status, and use the repaired service deployed from a hardened image."
```

Exact output, with terminal display wrapping removed:

```text
Sprint 3 planned — 23 item(s), 46/46 points
  TASK-016   P0 (1) Verify generated artefacts in the actual workspace before handoff
  TASK-017   P0 (1) Require regression tests when exception or validation coverage narrows
  TASK-021   P0 (1) Reject verification evasion and require discoverable test names
  BUG-019    P0 (2) Missing-project SDK failure bypasses every degradation policy
  TASK-028   P0 (3) Enforce a standing cross-layer compatibility gate for contract changes
  STORY-003  P1 (2) As an analyst I can trust the HVI rubric to rank zones consistently
  STORY-005  P1 (2) As an operator the product still works when BigQuery is unavailable
  STORY-007  P1 (3) As an ops lead I am alerted automatically when a zone becomes critical
  STORY-008  P1 (1) As an auditor I can trust the alert_dispatched flag on a stored scan
  STORY-011  P1 (2) As an operator the API rejects unsafe uploads before spending cloud budget
  STORY-012  P1 (2) As a frontend developer I get usable errors without leaked internals
  STORY-013  P1 (1) As an analyst I can list recent scans
  TASK-025   P1 (2) Harden the Dockerfile to the multi-stage non-root contract
  TASK-027   P1 (1) Document climate_source and the BigQuery location exception in the contract
  STORY-009  P2 (2) As an operator I can check whether the service and its dependencies are ready
  STORY-010  P2 (5) As an analyst I can upload an aerial image and receive a full heat report
  TASK-026   P2 (2) Declare a response model for POST /api/analyze
  STORY-017  P3 (3) As an analyst I can choose a city, temperature and image and run an analysis
  STORY-018  P3 (3) As an analyst I can see the HVI score and risk level at a glance
  STORY-019  P3 (3) As a city planner I can read the passive cooling blueprint
  STORY-020  P3 (1) As an ops lead I see confirmation that a critical alert was dispatched
  STORY-021  P3 (2) As a user the dashboard stays readable when something goes wrong
  TASK-013   P3 (1) Deploy and verify the repaired sprint 2 build on Cloud Run
```

The legacy TASK-013 title remains unchanged; its description now explicitly schedules the repaired sprint-3 build. Planning authorization is not live deployment evidence.

## Dependency and Container Checks

Executable assertions passed immediately after metadata updates and again after bl plan. All declared predecessors of every committed item are either already done or committed earlier in the actual (priority, created) order. No committed item depends on uncommitted unfinished work. STORY-029/030 and TASK-015 are explicitly deferred rather than silently presumed complete. All nine epics remain groomed with sprint=null; no epic was ready or committed. The 30 done records stayed unchanged. Sprint 3 has 23 in_sprint items and no in_progress items were created.

## File-Grouped Build Order

One specialist invocation per item. Each arrow means a separate sequential invocation, never one combined item. A cross-file item must acquire all its file locks atomically. The rows below are the exact declared file claims, not a claim that test/process ownership has already been resolved.

| File or ownership boundary           | Ordered committed items                                                                                           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| backend/services/vision_analyzer.py  | STORY-003                                                                                                         |
| backend/tools/climate_service.py     | BUG-019 -> STORY-005                                                                                              |
| backend/services/database.py         | BUG-019                                                                                                           |
| backend/tools/seed_samples.py        | BUG-019                                                                                                           |
| backend/services/alert_dispatcher.py | STORY-007 -> STORY-008                                                                                            |
| backend/main.py                      | STORY-008 -> STORY-011 -> STORY-012 -> STORY-013 -> STORY-009 -> STORY-010 -> TASK-026                            |
| frontend/app.py                      | STORY-017 -> STORY-018 -> STORY-019 -> STORY-020 -> STORY-021                                                     |
| frontend/.streamlit/config.toml      | STORY-017                                                                                                         |
| backend/Dockerfile                   | TASK-025                                                                                                          |
| .dockerignore                        | TASK-025 (expected creation)                                                                                      |
| backend/.dockerignore                | TASK-025                                                                                                          |
| COPILOT_GUIDE.md                     | TASK-027                                                                                                          |
| agile/requirements.md                | TASK-027                                                                                                          |
| No declared file claims (files=[])   | TASK-016 -> TASK-017 -> TASK-021; TASK-028 exclusive before contract stories; TASK-013 exclusive deployment last. |

BUG-019 is ONE invocation holding climate_service.py, database.py and seed_samples.py simultaneously. STORY-008 is ONE invocation holding alert_dispatcher.py and main.py simultaneously. STORY-017 holds app.py and config.toml simultaneously. TASK-025 holds all three packaging files; TASK-027 holds both contract documents. Do not create separate agents for each row of a cross-file item.

Undeclared files are not permission for parallel writes: TASK-016/017/021/028 must run alone and declare concrete process/check ownership before dispatch. Each later invocation must also declare its test, fixture, helper, instruction, manifest and documentation write set. Additional overlapping claims serialize the invocations or move them to a later wave; do not assume shared conftest.py or test modules are safe. This plan does not invent file scopes for the no-claim items or authorize edits to .github/docs/.

## Wave Plan

| Wave                                     | Dispatch and wait condition                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0: prevention and repair                 | Run TASK-016 -> TASK-017 -> TASK-021 -> BUG-019 -> TASK-028 serially, each exclusive. TASK-017 precedes the narrowed-tuple repair; BUG-019 reserves its three modules. TASK-028 establishes the standing gate before any contract-touching story.                                                                                                                                                        |
| 1: disjoint service/document/image lanes | After wave 0 is accepted, STORY-003 (analyzer), STORY-005 (climate), STORY-007 (publisher), TASK-025 (packaging) and TASK-027 (contract docs) may run concurrently, one agent per item, only with disjoint complete write sets. Wait for all five accepted handoffs before wave 2. TASK-025 may build a candidate image here, but the final deploy image must be built from the later accepted revision. |
| 2: controller lane                       | Run STORY-008 -> STORY-011 -> STORY-012 -> STORY-013 -> STORY-009 -> STORY-010 -> TASK-026 serially on main.py. STORY-008 additionally locks publisher; the publisher lane is already finished. TASK-026 waits for STORY-010 and TASK-027; rerun affected standing checks after each change.                                                                                                             |
| 3: dashboard lane                        | After accepted wave 2 API/history/model contracts, run STORY-017 -> STORY-018 -> STORY-019 -> STORY-020 -> STORY-021 serially on app.py. STORY-017 additionally locks config.toml. Rubric and truthful-alert predecessors are accepted before display work.                                                                                                                                              |
| 4: final deployment                      | TASK-013 alone, only after accepted prior waves, green suite/required coverage/contract checks, passing TASK-028 gate and a hardened TASK-025 image rebuilt from the accepted revision. Later cloud-deployer records serving revision/source/digest, live health/analysis/history/low-critical evidence and rollback target. No deployment is performed during planning.                                 |

These waves permit only file-disjoint concurrency; (priority, created) remains the valid topological commitment order, not a requirement to idle independent lanes. Shared QA/check writers run separately from concurrent producer writers.

## Deferred Scope

Explicit human exclusions: STORY-029 and STORY-030 blocked until sprint 4; STORY-031; TASK-029, TASK-030, TASK-031 (OQ-4 only); TASK-015; BUG-006; TEST-001. EPIC-008 product work STORY-022/023/024/025 and TASK-005 remains out; TASK-028 is the expressly selected prevention exception. All EPIC-009 work STORY-026/027/028/032 and TASK-006 remains out. All epic containers remain groomed, including these two.

Additional unselected records retained from grooming: STORY-014/015/016 and TASK-004; TASK-011/014/018/019/020/022/023. In total 30 unfinished executable items / 58 points remain outside sprint 3; this is deferred backlog, not sprint-3 carry-over.

## Final bl stats

```json
{
  "current_sprint": 3,
  "total": 92,
  "open": 62,
  "open_bugs": 2,
  "by_status": {"groomed": 20, "in_sprint": 23, "done": 30, "blocked": 19},
  "by_type": {"epic": 9, "story": 32, "task": 31, "bug": 19, "test": 1},
  "loop_done": false
}
```

Sprint goal and commitment are recorded. Single next action: on a fresh Phase 5 instruction, dispatch TASK-016 alone and establish concrete file ownership before subsequent handoffs. STOP at Phase 4; no development, QA, deployment, retrospective or sign-off gate is started by this planning request.

## Superseded Conditional Plan

The remaining sections preserve accepted grooming and the unresolved conditional plan before the five human rulings. They are historical evidence only, not current status or dispatch instructions.

## Decision Table

This records every status/priority change made in this session. No item was marked done, committed, or started. Each grouped row applies individually to every named item.

| Item                                                       | Old state  | New state  | Why                                                                                                            |
| ---------------------------------------------------------- | ---------- | ---------- | -------------------------------------------------------------------------------------------------------------- |
| BUG-019                                                    | new/P1     | ready/P0   | Confirmed cloud-construction failure escapes fallback/error boundaries; mandatory repair.                      |
| STORY-005                                                  | ready/P2   | ready/P1   | Telemetry degradation is a service prerequisite of end-to-end analysis.                                        |
| STORY-008                                                  | blocked/P2 | ready/P1   | STORY-006 shipped; proposed STORY-007 is sequencing, not an external blocker.                                  |
| STORY-012                                                  | ready/P2   | ready/P1   | HTTP error handling precedes full analysis acceptance.                                                         |
| STORY-013                                                  | ready/P2   | ready/P1   | History precedes dashboard work.                                                                               |
| STORY-029                                                  | blocked/P2 | blocked/P1 | API identity precedes full analysis; unresolved STORY-030 contract remains a real blocker.                     |
| STORY-030                                                  | blocked/P2 | blocked/P1 | Cannot rank below dependent STORY-029; serialized provenance remains unresolved and out of scope.              |
| TASK-017                                                   | ready/P1   | ready/P0   | Active exception-regression gate must rank before third consecutive recurrence BUG-019.                        |
| TASK-026                                                   | new/P1     | ready/P2   | Workable HTTP response-model slice; follows contract documentation TASK-027 and controller assembly.           |
| TASK-027                                                   | new/P1     | ready/P1   | Document accepted climate provenance/location exceptions before response-model acceptance.                     |
| TASK-028                                                   | new/P1     | ready/P0   | Standing compatibility gate addresses repeated schema/async/MIME integration failures before deployment.       |
| TASK-029                                                   | new/P1     | groomed/P2 | Valid QA attribution prevention, explicitly deferred.                                                          |
| TASK-030                                                   | new/P1     | groomed/P2 | Valid capacity-control prevention, explicitly deferred; this report preserves baseline/stretch arithmetic.     |
| TASK-031                                                   | new/P1     | blocked/P1 | Requires human answers, not an agent-selected numerical ruling.                                                |
| TASK-013                                                   | blocked/P1 | blocked/P3 | Deployment must run last; human scheduling intent is recorded, but TASK-015 live evidence remains unavailable. |
| STORY-017                                                  | blocked/P2 | blocked/P3 | Dashboard controls follow the complete API; unresolved backend dependencies remain.                            |
| STORY-018                                                  | blocked/P2 | blocked/P3 | HVI display follows dashboard controls and currently declared STORY-003 prerequisite.                          |
| STORY-019                                                  | blocked/P2 | blocked/P3 | Blueprint presentation follows dashboard controls.                                                             |
| STORY-020                                                  | blocked/P2 | blocked/P3 | Alert presentation follows controls and service provenance.                                                    |
| STORY-021                                                  | blocked/P2 | blocked/P3 | Error states follow controls; human timeout limits remain unresolved.                                          |
| STORY-003, STORY-022                                       | ready/P2   | groomed/P2 | Explicitly excluded stories; fence them out of the planner's all-ready intake.                                 |
| TASK-004, TASK-014, TASK-018, TASK-019, TASK-020, TASK-023 | ready/P2   | groomed/P2 | Explicitly deferred operational/process work; keep out of automatic commitment.                                |
| BUG-006, TEST-001                                          | ready/P2   | groomed/P2 | Explicit human exclusions; no completion claim.                                                                |

Additional metadata changes: STORY-008's description removes the obsolete external-blocker label; TASK-013 now explicitly names BUG-019, TASK-025, TASK-015, STORY-010, STORY-013 and TASK-028 before live deployment; TASK-025's file scope now includes backend/Dockerfile, root .dockerignore and backend/.dockerignore. The root ignore file is an expected creation, not an existing file. All estimates are unchanged. All nine epic containers remain groomed.

## Decision and Evidence

Phase 3's actionable grooming is recorded. Phase 4 is BLOCKED: no dependency-closed, human-resolved commitment exists for the requested outcome. Sprint 3 has not been created. This is not a sprint sign-off verdict.

Read phases 3-4 first, then the loop skill, requirements, guide, story blueprint, actual backlog and cmd_plan. Inspected the controlling API, cloud service boundaries, seeder, publisher, dashboard and Dockerfile. The missing-project exception gap and root-context mismatch are present. The analyzer exposes a whole coordinates override, but no per-field provenance representation; STORY-029's dependency on STORY-030 is not safely removable by grooming.

Verified baseline: 92 items; 104 remaining executable points; 30 done items; sprint 2 closed with 14 completed committed items and 21 points. Sprint 2's original 15-point plan was explicitly expanded by 6 emergency points. User-supplied 208 passing tests and 90.9% backend coverage were not rerun or independently remeasured in these planning phases. Two open backlog bugs exist: mandatory BUG-019 and explicitly deferred BUG-006; BUG-019 is the one selected product correctness defect, not literally the only open bug record.

45 points exceeds evidence-based velocity of 21 by 24 points (2.14 times measured delivery). This is the human-authorized stretch target, not demonstrated capacity. Carry-over is expected and acceptable. Nothing is committed over capacity, and stretch authorization does not resolve contract or numerical decisions.

## Scope and Recurrence Prevention

| Area                     | Verified IDs and estimates                                                                                            | Points |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- | ------ |
| Climate                  | STORY-005 (2), BUG-019 (2)                                                                                            | 4      |
| Alerts/persistence       | STORY-007 (3), STORY-008 (1)                                                                                          | 4      |
| API                      | STORY-009 (2), STORY-010 (5), STORY-011 (2), STORY-012 (2), STORY-013 (1), STORY-029 (3), STORY-031 (3), TASK-026 (2) | 20     |
| Dashboard                | STORY-017 (3), STORY-018 (3), STORY-019 (3), STORY-020 (1), STORY-021 (2)                                             | 12     |
| Shipping                 | TASK-025 (2), TASK-013 (1)                                                                                            | 3      |
| Contract documentation   | TASK-027 (1)                                                                                                          | 1      |
| Original intended scope  | 20 items                                                                                                              | 44     |
| Prevention               | TASK-016 (1), TASK-017 (1), TASK-021 (1), TASK-028 (3)                                                                | 6      |
| Combined candidate scope | 24 items                                                                                                              | 50     |
| Proposed cuts            | STORY-031 (3), STORY-009 (2)                                                                                          | -5     |
| Conditional target       | 22 items, not a commitment                                                                                            | 45     |

Pull TASK-017: BUG-005, BUG-014 and BUG-019 show three consecutive missed exception bases. Establish the same-change construction/operation failure matrix before BUG-019, retaining TypeError/KeyError propagation; do not defer prevention a third time.

Pull TASK-028: this sprint changes producer/API/UI contracts extensively. A standing offline compatibility gate must run on each affected change and again before deployment, not wait for a sprint-later audit. It complements rather than replaces TASK-026's response model. Establish the gate early and retain it throughout the sprint.

Also reserve TASK-016 and TASK-021: their sprint-1 findings recurred in sprint 2, and the user excepted these prevention tasks from the process-work exclusion. Together prevention consumes 6 points.

Proposed cuts preserve scored reports, Firestore persistence, alerts and rendering: STORY-031 adds GCS artifact retention beyond the required persisted report; STORY-009 adds independent cloud readiness beyond the existing health-200 endpoint. Deferring readiness means not claiming full dependency health. These cuts still do not resolve the external prerequisites below and therefore do not authorize planning.

## Blocker Review

All 28 initially blocked records were reevaluated. No additional eight stale shipped-foundation blockers were found: sprint 2 already removed those. STORY-008's obsolete external-prerequisite label was cleared because STORY-007 is proposed alongside it; this is conditional same-sprint sequencing, not evidence that STORY-007 shipped. No committed item has been left blocked on a committed prerequisite because no commitment has occurred.

| Item(s)   | Remaining reason / review result                                                                                                                                             |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STORY-008 | Cleared to ready; STORY-006 done, STORY-007 proposed before it.                                                                                                              |
| STORY-009 | STORY-005/007 proposed sequencing; OQ-5 readiness limits unresolved; proposed cut.                                                                                           |
| STORY-010 | STORY-003 excluded; STORY-029 depends on excluded/unagreed STORY-030; OQ-2 plausible-temperature limits unresolved. Other proposed API/service prerequisites are sequencing. |
| STORY-011 | OQ-2 exact byte limit needs human confirmation. Current 10,000,000 is a prior agent ruling, explicitly disputed by TASK-031, not a human answer.                             |
| STORY-014 | API/image hardening acceptance not committed; STORY-010/013/TASK-025 proposed only.                                                                                          |
| STORY-015 | STORY-014 and TASK-004 uncommitted.                                                                                                                                          |
| STORY-016 | STORY-015 uncommitted; STORY-010 not yet committed.                                                                                                                          |
| STORY-017 | Full API and identity prerequisites blocked; proposed sequence is not a substitute for those decisions.                                                                      |
| STORY-018 | STORY-017 blocked and STORY-003 explicitly excluded.                                                                                                                         |
| STORY-019 | STORY-017 blocked; analyzer prerequisite STORY-001 shipped.                                                                                                                  |
| STORY-020 | STORY-017 blocked; STORY-008 ready for proposed same-sprint sequencing.                                                                                                      |
| STORY-021 | STORY-017 blocked; OQ-5 human timeout limits unresolved. Current requests timeout tuple (5, 60) is implementation evidence, not confirmed acceptance limits.                 |
| STORY-023 | STORY-022/003/030 uncommitted; STORY-005/007 proposed; STORY-001/004/006 shipped.                                                                                            |
| STORY-024 | STORY-022 uncommitted; full API candidates still unresolved/uncommitted.                                                                                                     |
| STORY-025 | STORY-022/030 uncommitted; STORY-001 shipped.                                                                                                                                |
| TASK-005  | STORY-023/024/025 uncommitted.                                                                                                                                               |
| STORY-026 | STORY-015 uncommitted; foundation shipped.                                                                                                                                   |
| STORY-027 | STORY-031 proposed cut and uncommitted; STORY-010/008 proposed only.                                                                                                         |
| STORY-028 | STORY-016/026 uncommitted; dashboard proposed; OQ-4 constraints unresolved.                                                                                                  |
| TASK-006  | Demo/submission/deploy/coverage prerequisites uncommitted; OQ-4 unresolved.                                                                                                  |
| STORY-029 | STORY-030's provenance contract unresolved and expressly excluded.                                                                                                           |
| STORY-030 | Product-owner/contract-auditor agreement on serialized per-field provenance remains absent.                                                                                  |
| STORY-031 | STORY-010 unresolved; STORY-006 shipped; proposed cut.                                                                                                                       |
| STORY-032 | Identity/upload work unresolved; byte-limit decision missing.                                                                                                                |
| TASK-011  | Human-owned protected documentation correction; no editing authorization.                                                                                                    |
| TASK-013  | TASK-015 human provisioning/live evidence remains uncommitted. End-of-sprint deployment intent is accepted; do not deploy now or bypass later confirmation.                  |
| TASK-015  | Human-run provisioning, real Vertex connectivity and actual three GCS sample objects not demonstrated. Successful historical source deployment is insufficient.              |
| TASK-022  | TASK-012 verified the template via subprocess; it did not establish approved routine editor access, which is this separate task's criterion.                                 |
| TASK-031  | Newly classified blocked: needs human decisions for OQ-2/4/5; no values invented.                                                                                            |

## Verified Ready Queue

Actual cmd_plan sort: priority then created, retaining backlog order for ties. Epics are excluded. This is the real queue after grooming, not the proposed commitment.

| Order | Item           | Priority | Points |
| ----- | -------------- | -------- | ------ |
| 1     | TASK-017       | P0       | 1      |
| 2     | BUG-019        | P0       | 2      |
| 3     | TASK-028       | P0       | 3      |
| 4     | STORY-005      | P1       | 2      |
| 5     | STORY-007      | P1       | 3      |
| 6     | STORY-008      | P1       | 1      |
| 7     | STORY-012      | P1       | 2      |
| 8     | STORY-013      | P1       | 1      |
| 9     | TASK-016       | P1       | 1      |
| 10    | TASK-021       | P1       | 1      |
| 11    | TASK-025       | P1       | 2      |
| 12    | TASK-027       | P1       | 1      |
| 13    | TASK-026       | P2       | 2      |
| Total | 13 executables |          | 22     |

## Sprint Goal and Plan Output

Proposed goal: An analyst can open the dashboard, upload an aerial image, and receive a scored heat report grounded in real telemetry, persisted with truthful critical-alert status and rendered against the deployed service.

Pending command: `bl plan --capacity 45 --goal "An analyst can open the dashboard, upload an aerial image, and receive a scored heat report grounded in real telemetry, persisted with truthful critical-alert status and rendered against the deployed service."`

Exact bl plan output: NONE. The command was not executed because it would select only 13 ready items/22 points, omit required blocked product/deploy work and create a misleading sprint. Sprint 3 has no commitment, so dependency closure cannot honestly be confirmed. The proposed 45-point target is not closed over STORY-003, STORY-030 or TASK-015, and numerical criteria remain unanswered. Do not dispatch Phase 5 from this conditional report.

## Historical File-Grouped Build Order

This is a conditional routing map, not authorization to develop. One specialist invocation per executable; QA and contract checks accompany each handoff. Serialize all overlapping file claims, including BUG-019 and the two cross-file stories. Different nonoverlapping files can run concurrently only after their prerequisites and the standing checks are established.

| File / claim group                                         | Sequential order and cross-file barrier                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Process gate files not assigned in backlog                 | TASK-016, TASK-017, TASK-021 and TASK-028 currently have files=[]; specialist must declare concrete ownership before parallel dispatch. Establish workspace-evidence/test-integrity gates and exception regression requirement before repair; establish compatibility gate before contract-changing work.                                                                                                                                                                                                     |
| COPILOT_GUIDE.md + agile/requirements.md                   | TASK-027 before TASK-026 acceptance. Human/product-owner decisions belong here, not protected .github/docs. Do not guess doc_id/provenance schema alignment.                                                                                                                                                                                                                                                                                                                                                  |
| backend/tools/climate_service.py                           | BUG-019 then STORY-005. BUG-019 simultaneously owns database.py and seed_samples.py; reserve all three files for its invocation.                                                                                                                                                                                                                                                                                                                                                                              |
| backend/tools/seed_samples.py                              | BUG-019; no competing selected item.                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| backend/services/database.py                               | BUG-019; STORY-006 already shipped. If STORY-031 is restored, it also claims this file after STORY-010.                                                                                                                                                                                                                                                                                                                                                                                                       |
| backend/services/alert_dispatcher.py                       | STORY-007 then STORY-008. STORY-008 also owns main.py; acquire both claims, not parallel invocations.                                                                                                                                                                                                                                                                                                                                                                                                         |
| backend/main.py                                            | STORY-012 -> STORY-013 -> STORY-011 -> STORY-008 -> STORY-029 -> STORY-010 -> TASK-026. STORY-008 waits for STORY-007 and reserves publisher too. STORY-029 waits for provenance decision/producer dependency. STORY-010 waits for STORY-005/008/011/012/029 and resolution of declared STORY-003 dependency. TASK-026 waits for TASK-027. STORY-009 and STORY-031 are proposed cuts; if restored, readiness follows service repairs and storage follows STORY-010, with all relevant file claims serialized. |
| frontend/app.py + frontend/.streamlit/config.toml          | STORY-017 first, after accepted API/history/identity contracts; it alone additionally claims config.toml. Then serialize STORY-018 -> STORY-019 -> STORY-020 -> STORY-021 on app.py. STORY-018 also needs disposition of STORY-003; STORY-021 needs confirmed timeout criteria.                                                                                                                                                                                                                               |
| backend/Dockerfile + .dockerignore + backend/.dockerignore | TASK-025; define reproducible root-context non-root runtime, exclude credentials at the root context, honor PORT and remove mutable tooling. Can overlap API/UI work if manifests and gate ownership do not overlap; final build uses accepted current backend.                                                                                                                                                                                                                                               |
| Deployment, no production file claimed                     | TASK-013 last: TASK-025 image passes; BUG-019/API repairs accepted; TASK-028 compatibility gate green; TASK-015 live evidence available; required suite/coverage/contract checks green; explicit deploy confirmation; live health/report/history/low-critical evidence and rollback target recorded.                                                                                                                                                                                                          |

## Deferred Items

Explicit exclusions retained: STORY-022/023/024/025 and TASK-005; STORY-026/027/028/032 and TASK-006; BUG-006; TEST-001; STORY-003; STORY-030; EPIC-001 process work except proposed TASK-016/017/021. TASK-028 is the requested prevention exception to broad EPIC-008 deferral. TASK-029/030 are groomed and deferred; TASK-031 remains human-blocked. Other unscheduled shipping work: STORY-014/015/016 and TASK-004. Proposed point-balanced cuts: STORY-009 and STORY-031. Nothing has yet become sprint-3 carry-over because there is no sprint-3 commitment.

## Verification and Final Stats

Executable post-update assertions pass: current_sprint=2; 30 done unchanged; no new items; all nine epics groomed; ready records have criteria, parents and estimates no greater than 8; actual ordering places TASK-017 before BUG-019. The first check incorrectly expected 34 done, was corrected to the observed 30 and rerun successfully; no backlog repair or done transition occurred. Production code, tests and protected documentation were not edited; no Phase 5, deployment or test-suite run occurred.

Final `bl stats`:

```json
{
  "current_sprint": 2,
  "total": 92,
  "open": 62,
  "open_bugs": 2,
  "by_status": {"groomed": 21, "ready": 13, "done": 30, "blocked": 28},
  "by_type": {"epic": 9, "story": 32, "task": 31, "bug": 19, "test": 1},
  "loop_done": false
}
```

Single next action: obtain a human/product-owner ruling on (1) STORY-003/030 dependency disposition without silently dropping provenance criteria, (2) exact upload bytes, plausible temperature range and readiness/request timeout limits, and (3) TASK-015 live provisioning evidence or its inclusion before TASK-013; then rebaseline the point-balanced queue and run Phase 4 once dependency closure is real. OQ-4 submission limits can remain deferred with the submission scope.


