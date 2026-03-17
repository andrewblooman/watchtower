"""Local ephemeral filesystem cache for investigation sessions."""
from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import settings


def _cache_root() -> Path:
    return Path(settings.cache_dir)


def session_dir(session_id: str) -> Path:
    return _cache_root() / session_id


def read_json(session_id: str, relative_path: str) -> dict[str, Any] | None:
    """Read a JSON file from the session cache. Returns None if not found."""
    p = session_dir(session_id) / relative_path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl(session_id: str, relative_path: str) -> list[dict[str, Any]]:
    """Read a JSONL file from the session cache. Returns empty list if not found."""
    p = session_dir(session_id) / relative_path
    if not p.exists():
        return []
    lines = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                lines.append(json.loads(line))
            except Exception:
                pass
    return lines


def list_sessions() -> list[dict[str, Any]]:
    """List all sessions in the local cache with their metadata."""
    root = _cache_root()
    if not root.exists():
        return []
    sessions = []
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "session.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["source"] = "cache"
            sessions.append(meta)
        except Exception:
            pass
    return sessions


def list_artifacts(session_id: str) -> list[str]:
    """List artifact filenames for a session."""
    artifacts_dir = session_dir(session_id) / "artifacts"
    if not artifacts_dir.exists():
        return []
    return sorted(f.name for f in artifacts_dir.iterdir() if f.is_file())


def get_artifact_path(session_id: str, filename: str) -> Path | None:
    """Resolve an artifact path with path-traversal protection."""
    artifacts_dir = (session_dir(session_id) / "artifacts").resolve()
    candidate = (artifacts_dir / filename).resolve()
    if artifacts_dir not in candidate.parents and candidate != artifacts_dir:
        return None
    if not candidate.exists():
        return None
    return candidate


def sweep_expired_sessions() -> list[str]:
    """Remove sessions older than cache_ttl_hours. Returns removed session IDs."""
    root = _cache_root()
    if not root.exists():
        return []
    cutoff = datetime.now(UTC) - timedelta(hours=settings.cache_ttl_hours)
    removed: list[str] = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        meta_file = d / "session.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            started_at_str = meta.get("started_at", "")
            started_at = datetime.fromisoformat(started_at_str)
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            if started_at < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed.append(d.name)
        except Exception:
            pass
    return removed
