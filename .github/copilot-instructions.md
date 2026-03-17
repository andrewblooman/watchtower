# Copilot Instructions for SRE Agent Dashboard

## Quick Reference

### Build & Run
```bash
# Full stack with Docker Compose (fastest way to test end-to-end)
docker compose up --build

# Components start on:
# - UI: http://localhost:3000
# - API: http://localhost:8000/healthz
# - Postgres: localhost:5432 (user: sre_agent, pass: sre_agent)
```

### Local Development (without Docker)
```bash
# API (Python)
cd api
pip install -r requirements.txt
# Requires Postgres running. Set DATABASE_URL before starting
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Agent (Python)
cd agent
pip install -r requirements.txt
python -m agent.main

# UI (Node.js)
cd ui
npm install
npm run dev  # http://localhost:3000
```

### Database
- **Alembic** migrations in `api/alembic/`
- Auto-upgrade runs on API startup (SQLAlchemy init)
- Database: Postgres 16 (configured in docker-compose.yml)

## Architecture Overview

### Three Services
1. **UI (Next.js + React + Tailwind)**
   - Modern dashboard served on `:3000`
   - Calls API via `NEXT_PUBLIC_API_BASE` env var
   - Static + dynamic routes in `src/app/`
   - Recharts for incident/metrics visualization

2. **API (FastAPI + SQLAlchemy + AsyncPG)**
   - Event ingestion at `POST /v1/ingest/event` (requires API key auth)
   - Read endpoints for dashboard, incidents, events, artifacts
   - Multi-tenant design: tenant → services → environments → incidents/runs
   - Artifact downloads with path security (no path traversal)

3. **Agent (Python async client)**
   - Persists on the host, reads logs from `sample-data/logs/`
   - Ingests events into API every `INTERVAL_SECONDS` (default 10s)
   - Simulates test runs and incident detection
   - Uploads artifacts to shared volume

### Data Model
**Core entities:**
- `Tenant` → many `Service` + `Environment` (multi-tenant scoping)
- `Run` (deployment/test run, has version and status: healthy/degraded/rolled_back)
- `Incident` (scoped to tenant/service/environment, status: analyzing/rollback_in_progress/resolved)
- `Event` (atomic events: test_failed, log_detected, rollback_started, recommendation, incident_resolved, etc.)
- `Artifact` (logs, traces, RCA docs; tied to run or incident)

**Event Types & Incident Lifecycle:**
- Opening incident: `event_type in {"log_detected", "test_failed", "rollback_started"}` or `meta.open_incident=true`
- Resolving incident: `event_type in {"incident_resolved", "recovery_detected"}` or `meta.resolve_incident=true`
- Rollback: sets run status to `rolled_back` and incident status to `rollback_in_progress`

## Key Conventions

### API Endpoints
- All return JSON with Pydantic schemas (see `app/schemas.py`)
- Filters require `tenant_id`, `service_id`, `environment_id` (use `/v1/filters` to get UUIDs)
- List endpoints use `limit` query param (default 50–200, max 1000)
- Incident status filter: `?status=active` (default) or `?status=all`

### Authentication
- Ingest API key required for `POST /v1/ingest/event`
- Controlled by `INGEST_AUTH_DISABLED` env var (set to `"false"` for dev; `devkey` in compose)
- Check `app/auth.py:require_ingest_api_key`

### Database Queries
- Use SQLAlchemy async session: `session.execute(stmt)` + `.scalars().all()`
- Import models from `app/models.py`, schemas from `app/schemas.py`
- CRUD functions in `app/crud.py` (e.g., `create_incident`, `resolve_incident`, `dashboard_summary`)

### UI Patterns
- Components in `ui/src/components/`
- Tailwind utility classes (dark mode is default theme)
- Charts use Recharts (LineChart, AreaChart, PieChart)
- API calls assume `NEXT_PUBLIC_API_BASE` is set (defaults to `http://localhost:8000`)

### Configuration
- **API**: `app/config.py` (Pydantic Settings, reads from env)
- **Agent**: `agent/agent/config.py` (similar pattern)
- **UI**: Next.js env vars in docker-compose or `.env.local`
- Database URL: `postgresql+asyncpg://user:pass@host:port/dbname`

## Common Tasks

### Adding a New Event Type
1. Event is ingested via `POST /v1/ingest/event` with `type: string`
2. Logic for opening/resolving incidents is in `api/app/main.py:ingest_event()` (lines 79–84)
3. Add condition to `should_open_incident` or `should_resolve_incident` if needed
4. Event is persisted via `create_event()` in `app/crud.py`

### Adding a New Endpoint
1. Define Pydantic schema in `app/schemas.py`
2. Add route in `app/main.py` with `@app.get()` or `@app.post()`
3. Use `Depends(get_session)` for DB access
4. Return schema directly (FastAPI auto-serializes)

### Running Database Migrations
```bash
cd api
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Filtering by Tenant/Service/Environment
Always use the helper `_require_scope_ids()` (line 175 in main.py) to validate required query params and raise HTTP 400 if missing.

## Testing Notes
- No formal test suite in place (prototype phase)
- Sample data in `sample-data/logs/` used to seed the agent
- Manual testing via Docker Compose is primary validation method

## ECS/Fargate Deployment Notes
See `docs/ecs-migration.md` for production deployment design:
- UI behind ALB on public subnets
- API on private subnets (health checks on `/healthz`)
- Agent as long-lived service on private subnets
- Artifacts to migrate from local volume to S3
- Secrets Manager for API keys and DB credentials
