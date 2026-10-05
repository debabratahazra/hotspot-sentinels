# HotSpot Sentinels — Epic Catalogue

Every epic required to take this project from an empty workspace to a submitted hackathon entry. Each document is the authoritative scope for its epic; [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md) remains the authority on technical constraints and the Heat Analysis Result schema.

Progress below is derived from [agile/backlog.json](../../agile/backlog.json), which is the source of truth. EPIC-10 and EPIC-11 were added after this catalogue was first written and have no separate scope document; their stories live in the backlog.

## Epics

| Epic                                                      | Title                                    | Delivers                                       | Depends on | Progress    |
| --------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------- | ---------- | ----------- |
| [EPIC-01](./epics/EPIC-01-foundation-environment.md)      | Foundation & Environment                 | GCP provisioning, `.env`, deps, package layout | —          | 23/24       |
| [EPIC-02](./epics/EPIC-02-multimodal-perception.md)       | Multimodal Perception & Gemini Reasoning | `vision_analyzer.py`, `seed_samples.py`        | 01         | 5/5 done    |
| [EPIC-03](./epics/EPIC-03-climate-telemetry.md)           | Climate Telemetry & Ingestion            | `climate_service.py`                           | 01         | 5/5 done    |
| [EPIC-04](./epics/EPIC-04-resilience-pipeline.md)         | Event-Driven Resilience Pipeline         | `database.py`, `alert_dispatcher.py`           | 01         | 6/6 done    |
| [EPIC-05](./epics/EPIC-05-api-service.md)                 | FastAPI Core Service & Controller        | `main.py`                                      | 02, 03, 04 | 14/15       |
| [EPIC-06](./epics/EPIC-06-containerization-deployment.md) | Containerization & Cloud Run Deployment  | both `Dockerfile`s, live services              | 05         | 13/13 done  |
| [EPIC-07](./epics/EPIC-07-dashboard.md)                   | Interactive Dashboard & Heat Visualizer  | `frontend/app.py`                              | 05         | 11/11 done  |
| [EPIC-08](./epics/EPIC-08-quality-assurance.md)           | Quality Assurance & Test Coverage        | `tests/`, coverage reports                     | 02–07      | 14/14 done  |
| [EPIC-09](./epics/EPIC-09-demo-submission.md)             | Demo, Documentation & Submission         | README, demo runbook, submission               | 06, 07, 08 | 6/7         |
| EPIC-10 (backlog only)                                    | Coordinate-Based Maps Imagery            | `maps_imagery_service.py`, `/api/imagery`      | 05, 07     | 7/8         |
| EPIC-11 (backlog only)                                    | GitHub Actions CI/CD & Release           | `.github/workflows/`, branch protection        | 06, 08     | 5/6         |

The five incomplete items are listed with their reasons under **Known limitations** in the [root README](../../README.md).

## Dependency graph

```mermaid
flowchart LR
    E1[01 Foundation] --> E2[02 Perception]
    E1 --> E3[03 Climate]
    E1 --> E4[04 Resilience]
    E2 --> E5[05 API]
    E3 --> E5
    E4 --> E5
    E5 --> E6[06 Deployment]
    E5 --> E7[07 Dashboard]
    E6 --> E9[09 Demo]
    E7 --> E9
    E8[08 QA] --> E9
    E2 -.tests.-> E8
    E5 -.tests.-> E8
```

EPIC-08 runs alongside 02–07 rather than after them — tests are written in the same sprint as the code they cover, not retrofitted at the end.

## Traceability to the original backlog

[Epics_Stories.md](../../Epics_Stories.md) defined five build epics. This catalogue keeps all of them and adds the four an end-to-end delivery needs.

| Original                           | Here                                                                  |
| ---------------------------------- | --------------------------------------------------------------------- |
| Epic 1 Multimodal Perception       | EPIC-02                                                               |
| Epic 2 Climate Telemetry           | EPIC-03                                                               |
| Epic 3 Event-Driven Pipeline       | EPIC-04                                                               |
| Epic 4 FastAPI Service (Story 4.1) | EPIC-05                                                               |
| Epic 4 Docker (Story 4.2)          | EPIC-06, expanded to cover deploy, IAM and verification               |
| Epic 5 Streamlit UI                | EPIC-07                                                               |
| —                                  | EPIC-01 Foundation, implied by `setup_gcp.sh` but never scoped        |
| —                                  | EPIC-08 QA, required by the coverage reporting in the sprint workflow |
| —                                  | EPIC-09 Demo & submission, the actual hackathon deliverable           |

## How these feed the sprint workflow

Each epic document ends with a **Seed the backlog** block of `backlog.py` commands. Run them in epic order so the generated IDs line up with the document numbers — doc `EPIC-01` becomes backlog `EPIC-001`.

```bash
python3 .github/skills/agile-sdlc-loop/scripts/backlog.py init
# then paste each epic's seed block, in order
python3 .github/skills/agile-sdlc-loop/scripts/backlog.py list
```

After seeding, run `/agile-sdlc-loop sprint` to groom, plan, and deliver one sprint at a time.

## Status vocabulary

| Status      | Meaning                                                                             |
| ----------- | ----------------------------------------------------------------------------------- |
| Not started | No code exists                                                                      |
| In progress | Code exists but acceptance criteria are unmet — see the epic's known gaps           |
| Done        | Every story's acceptance criteria demonstrated, tests passing, contract audit clean |

Nothing is `Done` until EPIC-08's tests cover it. Code that exists is not code that works.
