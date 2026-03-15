from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Artifact, Environment, Event, Incident, Run, Service, Tenant


ACTIVE_INCIDENT_STATUSES = {"investigating", "analyzing", "rollback_in_progress"}


async def get_or_create_tenant(session: AsyncSession, name: str) -> Tenant:
    res = await session.execute(select(Tenant).where(Tenant.name == name))
    tenant = res.scalar_one_or_none()
    if tenant:
        return tenant
    tenant = Tenant(name=name)
    session.add(tenant)
    await session.flush()
    return tenant


async def get_or_create_service(session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Service:
    res = await session.execute(
        select(Service).where(and_(Service.tenant_id == tenant_id, Service.name == name))
    )
    service = res.scalar_one_or_none()
    if service:
        return service
    service = Service(tenant_id=tenant_id, name=name)
    session.add(service)
    await session.flush()
    return service


async def get_or_create_environment(session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Environment:
    res = await session.execute(
        select(Environment).where(and_(Environment.tenant_id == tenant_id, Environment.name == name))
    )
    env = res.scalar_one_or_none()
    if env:
        return env
    env = Environment(tenant_id=tenant_id, name=name)
    session.add(env)
    await session.flush()
    return env


async def get_run(session: AsyncSession, run_id: uuid.UUID) -> Run | None:
    res = await session.execute(select(Run).where(Run.id == run_id))
    return res.scalar_one_or_none()


async def create_run(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    environment_id: uuid.UUID,
    version: str | None,
) -> Run:
    run = Run(
        tenant_id=tenant_id,
        service_id=service_id,
        environment_id=environment_id,
        version=version,
        status="running",
    )
    session.add(run)
    await session.flush()
    return run


async def get_incident(session: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    res = await session.execute(select(Incident).where(Incident.id == incident_id))
    return res.scalar_one_or_none()


async def get_active_incident_for_scope(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    environment_id: uuid.UUID,
) -> Incident | None:
    res = await session.execute(
        select(Incident)
        .where(
            and_(
                Incident.tenant_id == tenant_id,
                Incident.service_id == service_id,
                Incident.environment_id == environment_id,
                Incident.status.in_(sorted(ACTIVE_INCIDENT_STATUSES)),
            )
        )
        .order_by(desc(Incident.detected_at))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def create_incident(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    environment_id: uuid.UUID,
    run_id: uuid.UUID,
    title: str,
    status: str = "investigating",
    root_cause_summary: str | None = None,
    confidence: float | None = None,
    detected_at: datetime | None = None,
) -> Incident:
    incident = Incident(
        tenant_id=tenant_id,
        service_id=service_id,
        environment_id=environment_id,
        run_id=run_id,
        title=title,
        status=status,
        root_cause_summary=root_cause_summary,
        confidence=confidence,
        detected_at=detected_at or datetime.now(UTC),
    )
    session.add(incident)
    await session.flush()
    return incident


async def resolve_incident(session: AsyncSession, incident: Incident, resolved_at: datetime | None = None) -> None:
    incident.status = "resolved"
    incident.resolved_at = resolved_at or datetime.now(UTC)
    await session.flush()


async def update_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    rollback_triggered: bool | None = None,
) -> None:
    stmt = update(Run).where(Run.id == run_id).values(status=status)
    if rollback_triggered is not None:
        stmt = stmt.values(rollback_triggered=rollback_triggered)
    await session.execute(stmt)


async def create_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    environment_id: uuid.UUID,
    run_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    event_type: str,
    message: str,
    ts: datetime,
    meta: dict,
) -> Event:
    event = Event(
        tenant_id=tenant_id,
        service_id=service_id,
        environment_id=environment_id,
        run_id=run_id,
        incident_id=incident_id,
        type=event_type,
        message=message,
        ts=ts,
        meta_json=meta or {},
    )
    session.add(event)
    await session.flush()
    return event


async def create_artifacts(
    session: AsyncSession,
    run_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    artifacts: list[dict],
) -> int:
    created = 0
    for a in artifacts:
        kind = str(a.get("kind") or "artifact")
        name = str(a.get("name") or kind)
        path_or_url = str(a.get("path_or_url") or "")
        if not path_or_url:
            continue
        session.add(
            Artifact(
                run_id=run_id,
                incident_id=incident_id,
                kind=kind,
                name=name,
                path_or_url=path_or_url,
            )
        )
        created += 1
    if created:
        await session.flush()
    return created


def start_of_utc_day(now: datetime) -> datetime:
    now = now.astimezone(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


async def dashboard_summary(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    environment_id: uuid.UUID,
) -> dict:
    now = datetime.now(UTC)
    day_start = start_of_utc_day(now)
    seven_days_ago = now - timedelta(days=7)

    active_incidents_q = await session.execute(
        select(func.count())
        .select_from(Incident)
        .where(
            and_(
                Incident.tenant_id == tenant_id,
                Incident.service_id == service_id,
                Incident.environment_id == environment_id,
                Incident.status.in_(sorted(ACTIVE_INCIDENT_STATUSES)),
            )
        )
    )
    active_incidents = int(active_incidents_q.scalar_one())

    tests_q = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(
            and_(
                Event.tenant_id == tenant_id,
                Event.service_id == service_id,
                Event.environment_id == environment_id,
                Event.type.in_(["test_passed", "test_failed"]),
                Event.ts >= day_start,
            )
        )
    )
    tests_executed_today = int(tests_q.scalar_one())

    rollbacks_q = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(
            and_(
                Event.tenant_id == tenant_id,
                Event.service_id == service_id,
                Event.environment_id == environment_id,
                Event.type == "rollback_started",
                Event.ts >= seven_days_ago,
            )
        )
    )
    recent_rollbacks = int(rollbacks_q.scalar_one())

    llm_q = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(
            and_(
                Event.tenant_id == tenant_id,
                Event.service_id == service_id,
                Event.environment_id == environment_id,
                Event.type == "recommendation",
                Event.ts >= seven_days_ago,
            )
        )
    )
    llm_insights_used = int(llm_q.scalar_one())

    return {
        "active_incidents": active_incidents,
        "tests_executed_today": tests_executed_today,
        "recent_rollbacks": recent_rollbacks,
        "llm_insights_used": llm_insights_used,
    }

