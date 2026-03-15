from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestArtifact(BaseModel):
    kind: str
    name: str
    path_or_url: str


class IngestEvent(BaseModel):
    tenant: str
    service: str
    environment: str
    version: str | None = None
    run_id: uuid.UUID | None = None
    incident_id: uuid.UUID | None = None
    type: str
    ts: datetime | None = None
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class IdName(BaseModel):
    id: uuid.UUID
    name: str


class FiltersResponse(BaseModel):
    tenants: list[IdName]
    services: list[IdName]
    environments: list[IdName]


class DashboardSummary(BaseModel):
    active_incidents: int
    tests_executed_today: int
    recent_rollbacks: int
    llm_insights_used: int


class IncidentRow(BaseModel):
    id: uuid.UUID
    service: str
    environment: str
    status: str
    title: str
    root_cause_summary: str | None
    detected_at: datetime


class IncidentDetail(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    service_id: uuid.UUID
    environment_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    title: str
    root_cause_summary: str | None
    confidence: float | None
    detected_at: datetime
    resolved_at: datetime | None


class EventRow(BaseModel):
    id: uuid.UUID
    ts: datetime
    type: str
    message: str
    meta: dict[str, Any]
    run_id: uuid.UUID
    incident_id: uuid.UUID | None


class ArtifactRow(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    path_or_url: str
    created_at: datetime
    run_id: uuid.UUID
    incident_id: uuid.UUID | None


class IngestResponse(BaseModel):
    tenant_id: uuid.UUID
    service_id: uuid.UUID
    environment_id: uuid.UUID
    run_id: uuid.UUID
    incident_id: uuid.UUID | None
    event_id: uuid.UUID
    created_artifacts: int = 0

