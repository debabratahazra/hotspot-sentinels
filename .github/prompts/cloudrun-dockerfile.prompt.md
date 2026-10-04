---
name: "Cloud Run Dockerfile"
description: "Scaffold backend/Dockerfile: a lightweight multi-stage python:3.11-slim image serving the FastAPI app with uvicorn on Cloud Run port 8080."
agent: "agent"
tools: ["edit", "search", "runCommands"]
---

Write the Cloud Run container definition for HotSpot Sentinels (Epic 4 / Story 4.2).

Project rules: [COPILOT_GUIDE.md](../../COPILOT_GUIDE.md).

## Target files

- `backend/Dockerfile`
- `backend/.dockerignore`

## Build context

`requirements.txt` lives at the repository root, so the image must be built from the root with `-f backend/Dockerfile .`. Write every `COPY` path relative to the repo root (`COPY requirements.txt .`, `COPY backend/ .`). A `./backend` build context cannot reach the requirements file.

## Requirements

- Multi-stage build on `python:3.11-slim`:
  - **builder** stage installs from [requirements.txt](../../requirements.txt) into a virtualenv or `--user` prefix with `--no-cache-dir`.
  - **runtime** stage copies only the installed packages and application source.
- `WORKDIR /app`; copy `requirements.txt` before the source so dependency layers cache.
- Set `PYTHONUNBUFFERED=1` and `PYTHONDONTWRITEBYTECODE=1`.
- Create and switch to a non-root user before `ENTRYPOINT`.
- `EXPOSE 8080` and start with `uvicorn main:app --host 0.0.0.0 --port 8080` in exec form; honour the Cloud Run `$PORT` variable if set.
- `.dockerignore` must exclude `venv/`, `.env`, `data_samples/`, `__pycache__/`, `.git/`, and any service-account key files — no credentials in the image.

## Done when

- `docker build -f backend/Dockerfile -t hotspot-sentinels .` succeeds from the repository root and the container answers `GET /api/health` on 8080.
