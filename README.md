# SRE Agent Dashboard (Prototype)

![Dashboard Screenshot](dashboard.png)

Fast demoable “AI Reliability Engineer Platform” that runs locally in Docker Compose:

- `agent` runs persistently, tails `sample-data/logs/`, simulates tests, and ingests events into the API.
- `api` (FastAPI) persists state in Postgres and serves dashboard read APIs.
- `ui` (Next.js + Tailwind) renders a dark dashboard with filters, KPIs, incidents, RCA, timelines, charts, and artifacts.

## Quickstart (Docker)

Prereqs: Docker Desktop (or Docker Engine) with Compose.

```bash
docker compose up --build
```

- UI: `http://localhost:3000`
- API health: `http://localhost:8000/healthz`

Within ~30–60 seconds the UI should show at least one active incident from the sample logs.

## Local dev (optional)

- API runs on `:8000`
- UI runs on `:3000` and calls the API via `NEXT_PUBLIC_API_BASE` (defaults to `http://localhost:8000` in compose)

## ECS migration notes

See `docs/ecs-migration.md`.

