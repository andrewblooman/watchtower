from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SessionMeta(BaseModel):
    session_id: str
    github_repo: str
    commit_sha: str
    commit_short: str
    service_name: str
    environment: str
    started_at: datetime
    status: str  # investigating | resolved | failed | timeout
    completed_at: datetime | None = None
    event_metadata: dict[str, Any] = {}
    source: str = "cache"  # cache | s3


class InvestigationSummary(BaseModel):
    session_id: str
    root_cause: str | None = None
    confidence: float | None = None
    recommendation: str | None = None
    commands_count: int = 0
    reasoning_turns: int = 0
    resolution: str | None = None  # resolved | unresolved


class CommandRecord(BaseModel):
    ts: datetime
    type: str  # shell | tool
    command: str
    args: dict[str, Any] | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    result: Any = None


class ReasoningTurn(BaseModel):
    ts: datetime
    turn: int
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    prompt_summary: str
    response: str


class SessionListItem(BaseModel):
    session_id: str
    github_repo: str
    commit_short: str
    service_name: str
    environment: str
    started_at: datetime
    status: str
    source: str  # cache | s3


class SessionDetail(BaseModel):
    session: SessionMeta
    summary: InvestigationSummary | None = None
    commands_count: int = 0
    reasoning_turns: int = 0
    artifacts: list[str] = []


class DashboardSummary(BaseModel):
    active_sessions: int
    completed_sessions: int
    total_sessions: int
    recent_repos: list[str]
