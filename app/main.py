from __future__ import annotations

import asyncio

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app import cache as local_cache
from app import s3_client
from app.config import settings
from app.schemas import (
    CommandRecord,
    DashboardSummary,
    InvestigationSummary,
    ReasoningTurn,
    SessionDetail,
    SessionListItem,
    SessionMeta,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_ttl_sweep_loop())
    yield
    task.cancel()


async def _ttl_sweep_loop() -> None:
    while True:
        await asyncio.sleep(3600)
        removed = local_cache.sweep_expired_sessions()
        if removed:
            print(f"[cache] Swept {len(removed)} expired session(s): {removed}", flush=True)


app = FastAPI(title="SRE Agent API", version="2.0.0", lifespan=lifespan)


def _all_sessions() -> list[dict[str, Any]]:
    """Merge sessions from local cache and S3, deduplicated by session_id."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for s in local_cache.list_sessions():
        sid = s.get("session_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            merged.append(s)
    for s in s3_client.list_sessions():
        sid = s.get("session_id", "")
        if sid and sid not in seen:
            seen.add(sid)
            merged.append(s)
    merged.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    return merged


def _find_session(session_id: str) -> dict[str, Any] | None:
    """Find session metadata by ID, checking cache first then S3."""
    meta = local_cache.read_json(session_id, "session.json")
    if meta:
        meta["source"] = "cache"
        return meta
    for s in s3_client.list_sessions():
        if s.get("session_id") == session_id:
            return s
    return None


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/v1/sessions", response_model=list[SessionListItem])
async def list_sessions(status: str | None = Query(default=None)) -> list[SessionListItem]:
    """List investigation sessions from local cache and S3."""
    items: list[SessionListItem] = []
    for s in _all_sessions():
        if status and s.get("status") != status:
            continue
        try:
            items.append(
                SessionListItem(
                    session_id=s["session_id"],
                    github_repo=s.get("github_repo", "unknown/unknown"),
                    commit_short=s.get("commit_short", "unknown"),
                    service_name=s.get("service_name", "unknown"),
                    environment=s.get("environment", "unknown"),
                    started_at=s["started_at"],
                    status=s.get("status", "investigating"),
                    source=s.get("source", "cache"),
                )
            )
        except Exception:
            pass
    return items


@app.get("/v1/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str) -> SessionDetail:
    meta = _find_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    source = meta.get("source", "cache")
    repo = meta.get("github_repo", "")
    commit_short = meta.get("commit_short", "")
    if source == "cache":
        summary_raw = local_cache.read_json(session_id, "summary.json")
        commands = local_cache.read_jsonl(session_id, "commands/history.jsonl")
        reasoning = local_cache.read_jsonl(session_id, "ai/reasoning.jsonl")
        artifacts = local_cache.list_artifacts(session_id)
    else:
        summary_raw = s3_client.read_json(session_id, repo, commit_short, "summary.json")
        commands = s3_client.read_jsonl(session_id, repo, commit_short, "commands/history.jsonl")
        reasoning = s3_client.read_jsonl(session_id, repo, commit_short, "ai/reasoning.jsonl")
        artifacts = s3_client.list_artifacts(session_id, repo, commit_short)
    summary = InvestigationSummary(**summary_raw) if summary_raw else None
    return SessionDetail(
        session=SessionMeta(**{**meta, "source": source}),
        summary=summary,
        commands_count=len(commands),
        reasoning_turns=len(reasoning),
        artifacts=artifacts,
    )


@app.get("/v1/sessions/{session_id}/commands", response_model=list[CommandRecord])
async def get_commands(session_id: str) -> list[CommandRecord]:
    meta = _find_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    source = meta.get("source", "cache")
    repo = meta.get("github_repo", "")
    commit_short = meta.get("commit_short", "")
    if source == "cache":
        records = local_cache.read_jsonl(session_id, "commands/history.jsonl")
    else:
        records = s3_client.read_jsonl(session_id, repo, commit_short, "commands/history.jsonl")
    return [CommandRecord(**r) for r in records]


@app.get("/v1/sessions/{session_id}/reasoning", response_model=list[ReasoningTurn])
async def get_reasoning(session_id: str) -> list[ReasoningTurn]:
    meta = _find_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    source = meta.get("source", "cache")
    repo = meta.get("github_repo", "")
    commit_short = meta.get("commit_short", "")
    if source == "cache":
        records = local_cache.read_jsonl(session_id, "ai/reasoning.jsonl")
    else:
        records = s3_client.read_jsonl(session_id, repo, commit_short, "ai/reasoning.jsonl")
    return [ReasoningTurn(**r) for r in records]


@app.get("/v1/sessions/{session_id}/artifacts")
async def list_session_artifacts(session_id: str) -> list[str]:
    meta = _find_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    source = meta.get("source", "cache")
    repo = meta.get("github_repo", "")
    commit_short = meta.get("commit_short", "")
    if source == "cache":
        return local_cache.list_artifacts(session_id)
    return s3_client.list_artifacts(session_id, repo, commit_short)


@app.get("/v1/sessions/{session_id}/artifacts/{filename}/download")
async def download_artifact(session_id: str, filename: str):
    meta = _find_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found")
    source = meta.get("source", "cache")
    repo = meta.get("github_repo", "")
    commit_short = meta.get("commit_short", "")
    if source == "cache":
        path = local_cache.get_artifact_path(session_id, filename)
        if not path:
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(path=str(path), filename=filename)
    data = s3_client.download_artifact(session_id, repo, commit_short, filename)
    if data is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/v1/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary() -> DashboardSummary:
    sessions = _all_sessions()
    active = sum(1 for s in sessions if s.get("status") == "investigating")
    completed = sum(1 for s in sessions if s.get("status") in {"resolved", "failed", "timeout"})
    repos: list[str] = list(
        dict.fromkeys(s.get("github_repo", "") for s in sessions if s.get("github_repo"))
    )
    return DashboardSummary(
        active_sessions=active,
        completed_sessions=completed,
        total_sessions=len(sessions),
        recent_repos=repos[:5],
    )


# ── Static UI (Next.js export) ────────────────────────────────────────────────
# Mounted last so all /v1/* API routes take priority.
# The _next/ sub-directory is mounted first to ensure correct asset MIME types.
_UI_DIR = Path(__file__).parent.parent / "ui_static"

if _UI_DIR.is_dir():
    _next_dir = _UI_DIR / "_next"
    if _next_dir.is_dir():
        app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="next_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        # Try exact file first (e.g. favicon.ico, images)
        candidate = (_UI_DIR / full_path).resolve()
        if _UI_DIR.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        # Fall back to index.html for client-side routing
        return FileResponse(_UI_DIR / "index.html")
