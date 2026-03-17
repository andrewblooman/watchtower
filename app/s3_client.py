"""S3 client for reading/writing investigation sessions to S3."""
from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def _s3():
    kwargs: dict[str, Any] = {"region_name": settings.s3_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", **kwargs)


def _prefix(path: str = "") -> str:
    base = settings.s3_prefix.rstrip("/")
    if path:
        return f"{base}/{path.lstrip('/')}"
    return base + "/"


def _find_session_key(s3_client, session_id: str) -> tuple[str, str, str] | None:
    """Search S3 for a session.json matching the given session_id.
    Returns (repo, commit_short, key_prefix) or None."""
    prefix = _prefix()
    paginator = s3_client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("/session.json"):
                    continue
                try:
                    body = s3_client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
                    meta = json.loads(body)
                    if meta.get("session_id") == session_id:
                        # key like: investigations/org/repo/abc1234/session.json
                        parts = key[len(prefix):].split("/")
                        if len(parts) >= 3:
                            repo = "/".join(parts[:-2])
                            commit_short = parts[-2]
                            return repo, commit_short, _prefix(f"{repo}/{commit_short}/")
                except Exception:
                    pass
    except ClientError:
        pass
    return None


def list_sessions() -> list[dict[str, Any]]:
    """List investigation sessions stored in S3 by scanning for session.json files."""
    s3 = _s3()
    prefix = _prefix()
    sessions: list[dict[str, Any]] = []
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("/session.json"):
                    continue
                try:
                    body = s3.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
                    meta = json.loads(body)
                    meta["source"] = "s3"
                    sessions.append(meta)
                except Exception:
                    pass
    except ClientError:
        pass
    return sessions


def read_json(session_id: str, repo: str, commit_short: str, relative_path: str) -> dict[str, Any] | None:
    """Read a JSON file for a session from S3."""
    s3 = _s3()
    key = _prefix(f"{repo}/{commit_short}/{relative_path}")
    try:
        body = s3.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
        return json.loads(body)
    except ClientError:
        return None


def read_jsonl(session_id: str, repo: str, commit_short: str, relative_path: str) -> list[dict[str, Any]]:
    """Read a JSONL file for a session from S3."""
    s3 = _s3()
    key = _prefix(f"{repo}/{commit_short}/{relative_path}")
    try:
        body = s3.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read().decode()
        lines = []
        for line in body.splitlines():
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
        return lines
    except ClientError:
        return []


def list_artifacts(session_id: str, repo: str, commit_short: str) -> list[str]:
    """List artifact filenames for a session in S3."""
    s3 = _s3()
    prefix = _prefix(f"{repo}/{commit_short}/artifacts/")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        names: list[str] = []
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                name = obj["Key"][len(prefix):]
                if name and "/" not in name:
                    names.append(name)
        return sorted(names)
    except ClientError:
        return []


def download_artifact(session_id: str, repo: str, commit_short: str, filename: str) -> bytes | None:
    """Download an artifact from S3. Returns None on failure or path traversal."""
    if "/" in filename or ".." in filename:
        return None
    s3 = _s3()
    key = _prefix(f"{repo}/{commit_short}/artifacts/{filename}")
    try:
        return s3.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
    except ClientError:
        return None
