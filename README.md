# watchtower
AI Powered SRE Agent

## Dashboard prototype (Docker → ECS)

This repo includes a fast demoable “AI Reliability Engineer Platform” that runs locally in Docker Compose:

- `agent` runs persistently, tails `sample-data/logs/`, simulates tests, and ingests events into the API.
- `api` (FastAPI) persists state in Postgres and serves dashboard read APIs.
- `ui` (Next.js + Tailwind) renders a dark dashboard with filters, KPIs, incidents, RCA, timelines, charts, and artifacts.

### Quickstart

```bash
docker compose up --build
```

- UI: `http://localhost:3000`
- API health: `http://localhost:8000/healthz`

Within ~30–60 seconds the UI should show at least one active incident from the sample logs.

### ECS notes

See `docs/ecs-migration.md`.
