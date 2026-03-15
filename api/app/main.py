from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_ingest_api_key
from app.config import settings
from app.crud import (
    ACTIVE_INCIDENT_STATUSES,
    create_artifacts,
    create_event,
    create_incident,
    create_run,
    dashboard_summary,
    get_active_incident_for_scope,
    get_incident,
    get_or_create_environment,
    get_or_create_service,
    get_or_create_tenant,
    get_run,
    resolve_incident,
    update_run_status,
)
from app.db import get_session
from app.models import Artifact, Environment, Event, Incident, Service, Tenant
from app.schemas import (
    ArtifactRow,
    DashboardSummary,
    EventRow,
    FiltersResponse,
    IncidentDetail,
    IncidentRow,
    IngestEvent,
    IngestResponse,
    IdName,
)

app = FastAPI(title="SRE Agent API", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/v1/ingest/event", response_model=IngestResponse, dependencies=[Depends(require_ingest_api_key)])
async def ingest_event(payload: IngestEvent, session: AsyncSession = Depends(get_session)) -> IngestResponse:
    tenant = await get_or_create_tenant(session, payload.tenant)
    service = await get_or_create_service(session, tenant.id, payload.service)
    env = await get_or_create_environment(session, tenant.id, payload.environment)

    run = await get_run(session, payload.run_id) if payload.run_id else None
    if not run:
        run = await create_run(session, tenant.id, service.id, env.id, payload.version)

    incident: Incident | None = await get_incident(session, payload.incident_id) if payload.incident_id else None

    ts = payload.ts or datetime.now(UTC)
    event_type = payload.type
    meta = payload.meta or {}

    should_open_incident = event_type in {"log_detected", "test_failed", "rollback_started"} or bool(
        meta.get("open_incident")
    )
    should_resolve_incident = event_type in {"incident_resolved", "recovery_detected"} or bool(
        meta.get("resolve_incident")
    )

    if not incident and should_open_incident:
        incident = await get_active_incident_for_scope(session, tenant.id, service.id, env.id)
        if not incident:
            title = str(meta.get("title") or payload.message[:120] or "Incident detected")
            incident = await create_incident(
                session,
                tenant.id,
                service.id,
                env.id,
                run.id,
                title=title,
                status="rollback_in_progress" if event_type == "rollback_started" else "analyzing",
                root_cause_summary=meta.get("root_cause_summary"),
                confidence=meta.get("confidence"),
                detected_at=ts,
            )

    if incident and event_type == "recommendation":
        if meta.get("root_cause_summary"):
            incident.root_cause_summary = str(meta["root_cause_summary"])
        if meta.get("confidence") is not None:
            try:
                incident.confidence = float(meta["confidence"])
            except Exception:
                pass

    if incident and should_resolve_incident:
        await resolve_incident(session, incident, resolved_at=ts)
        await update_run_status(session, run.id, status="healthy")

    if event_type == "rollback_started":
        await update_run_status(session, run.id, status="rolled_back", rollback_triggered=True)
        if incident:
            incident.status = "rollback_in_progress"

    if event_type in {"test_failed", "log_detected"}:
        await update_run_status(session, run.id, status="degraded")

    event = await create_event(
        session,
        tenant.id,
        service.id,
        env.id,
        run.id,
        incident.id if incident else None,
        event_type,
        payload.message,
        ts,
        meta,
    )

    created_artifacts = 0
    artifacts = meta.get("artifacts")
    if isinstance(artifacts, list):
        created_artifacts = await create_artifacts(session, run.id, incident.id if incident else None, artifacts)

    await session.commit()

    return IngestResponse(
        tenant_id=tenant.id,
        service_id=service.id,
        environment_id=env.id,
        run_id=run.id,
        incident_id=incident.id if incident else None,
        event_id=event.id,
        created_artifacts=created_artifacts,
    )


@app.get("/v1/filters", response_model=FiltersResponse)
async def get_filters(
    tenant_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> FiltersResponse:
    tenants = (await session.execute(select(Tenant).order_by(Tenant.name))).scalars().all()
    services_stmt = select(Service).order_by(Service.name)
    envs_stmt = select(Environment).order_by(Environment.name)
    if tenant_id:
        services_stmt = services_stmt.where(Service.tenant_id == tenant_id)
        envs_stmt = envs_stmt.where(Environment.tenant_id == tenant_id)
    services = (await session.execute(services_stmt)).scalars().all()
    envs = (await session.execute(envs_stmt)).scalars().all()
    return FiltersResponse(
        tenants=[IdName(id=t.id, name=t.name) for t in tenants],
        services=[IdName(id=s.id, name=s.name) for s in services],
        environments=[IdName(id=e.id, name=e.name) for e in envs],
    )


def _require_scope_ids(
    tenant_id: uuid.UUID | None,
    service_id: uuid.UUID | None,
    environment_id: uuid.UUID | None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    if not tenant_id or not service_id or not environment_id:
        raise HTTPException(status_code=400, detail="tenant_id, service_id, and environment_id are required")
    return tenant_id, service_id, environment_id


@app.get("/v1/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    tenant_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    environment_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    tenant_id, service_id, environment_id = _require_scope_ids(tenant_id, service_id, environment_id)
    data = await dashboard_summary(session, tenant_id, service_id, environment_id)
    return DashboardSummary(**data)


@app.get("/v1/incidents", response_model=list[IncidentRow])
async def list_incidents(
    tenant_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    environment_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default="active"),
    session: AsyncSession = Depends(get_session),
) -> list[IncidentRow]:
    tenant_id, service_id, environment_id = _require_scope_ids(tenant_id, service_id, environment_id)

    stmt = select(Incident).where(
        and_(
            Incident.tenant_id == tenant_id,
            Incident.service_id == service_id,
            Incident.environment_id == environment_id,
        )
    )
    if status == "active":
        stmt = stmt.where(Incident.status.in_(sorted(ACTIVE_INCIDENT_STATUSES)))
    stmt = stmt.order_by(desc(Incident.detected_at)).limit(50)
    incidents = (await session.execute(stmt)).scalars().all()

    service_name = (await session.execute(select(Service.name).where(Service.id == service_id))).scalar_one()
    env_name = (await session.execute(select(Environment.name).where(Environment.id == environment_id))).scalar_one()
    return [
        IncidentRow(
            id=i.id,
            service=service_name,
            environment=env_name,
            status=i.status,
            title=i.title,
            root_cause_summary=i.root_cause_summary,
            detected_at=i.detected_at,
        )
        for i in incidents
    ]


@app.get("/v1/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident_detail(incident_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> IncidentDetail:
    incident = (await session.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentDetail(
        id=incident.id,
        tenant_id=incident.tenant_id,
        service_id=incident.service_id,
        environment_id=incident.environment_id,
        run_id=incident.run_id,
        status=incident.status,
        title=incident.title,
        root_cause_summary=incident.root_cause_summary,
        confidence=incident.confidence,
        detected_at=incident.detected_at,
        resolved_at=incident.resolved_at,
    )


@app.get("/v1/events", response_model=list[EventRow])
async def list_events(
    tenant_id: uuid.UUID | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    environment_id: uuid.UUID | None = Query(default=None),
    incident_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[EventRow]:
    tenant_id, service_id, environment_id = _require_scope_ids(tenant_id, service_id, environment_id)
    stmt = select(Event).where(
        and_(
            Event.tenant_id == tenant_id,
            Event.service_id == service_id,
            Event.environment_id == environment_id,
        )
    )
    if incident_id:
        stmt = stmt.where(Event.incident_id == incident_id)
    stmt = stmt.order_by(desc(Event.ts)).limit(limit)
    events = (await session.execute(stmt)).scalars().all()
    return [
        EventRow(
            id=e.id,
            ts=e.ts,
            type=e.type,
            message=e.message,
            meta=e.meta_json or {},
            run_id=e.run_id,
            incident_id=e.incident_id,
        )
        for e in events
    ]


@app.get("/v1/artifacts", response_model=list[ArtifactRow])
async def list_artifacts(
    run_id: uuid.UUID | None = Query(default=None),
    incident_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactRow]:
    if not run_id and not incident_id:
        raise HTTPException(status_code=400, detail="run_id or incident_id is required")

    stmt = select(Artifact)
    if run_id:
        stmt = stmt.where(Artifact.run_id == run_id)
    if incident_id:
        stmt = stmt.where(Artifact.incident_id == incident_id)
    stmt = stmt.order_by(desc(Artifact.created_at)).limit(limit)
    artifacts = (await session.execute(stmt)).scalars().all()
    return [
        ArtifactRow(
            id=a.id,
            kind=a.kind,
            name=a.name,
            path_or_url=a.path_or_url,
            created_at=a.created_at,
            run_id=a.run_id,
            incident_id=a.incident_id,
        )
        for a in artifacts
    ]


@app.get("/v1/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> FileResponse:
    artifact = (await session.execute(select(Artifact).where(Artifact.id == artifact_id))).scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.path_or_url.startswith("http://") or artifact.path_or_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Artifact is not a local file")

    artifacts_dir = Path(settings.artifacts_dir).resolve()
    candidate = (artifacts_dir / artifact.path_or_url).resolve()
    if artifacts_dir not in candidate.parents and candidate != artifacts_dir:
        raise HTTPException(status_code=400, detail="Invalid artifact path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")

    return FileResponse(path=str(candidate), filename=os.path.basename(candidate))
