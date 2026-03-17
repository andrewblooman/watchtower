"""Investigation session lifecycle: local cache + S3 flush on completion."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from agent.config import settings


class InvestigationSession:
    """Manages a single investigation session.

    Writes all data (logs, commands, reasoning, artifacts) to the local
    ephemeral cache during the investigation. On completion, flushes
    everything to S3 at: s3://{bucket}/{prefix}/{repo}/{commit_short}/
    """

    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.started_at = datetime.now(UTC)
        self.commit_short = settings.commit_sha[:7]
        self.status = "investigating"
        self._cache_root = Path(settings.cache_dir) / self.session_id
        for sub in ("logs", "commands", "ai", "artifacts"):
            (self._cache_root / sub).mkdir(parents=True, exist_ok=True)
        self._write_session_meta()
        print(
            f"[session] Started {self.session_id} "
            f"({settings.github_repo}@{self.commit_short})",
            flush=True,
        )

    # ── Metadata ──────────────────────────────────────────────────────────────

    def _write_session_meta(self) -> None:
        meta = {
            "session_id": self.session_id,
            "github_repo": settings.github_repo,
            "commit_sha": settings.commit_sha,
            "commit_short": self.commit_short,
            "service_name": settings.service_name,
            "environment": settings.environment,
            "started_at": self.started_at.isoformat(),
            "status": self.status,
            "completed_at": None,
            "event_metadata": {},
        }
        (self._cache_root / "session.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    # ── Append helpers ────────────────────────────────────────────────────────

    def append_log(self, log_group: str, events: list[dict[str, Any]]) -> None:
        """Append CloudWatch log events for a log group."""
        safe_name = log_group.replace("/", "_").lstrip("_") + ".jsonl"
        with (self._cache_root / "logs" / safe_name).open("a", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def append_command(self, record: dict[str, Any]) -> None:
        """Append a shell command or AWS tool call record."""
        with (self._cache_root / "commands" / "history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def append_reasoning(self, record: dict[str, Any]) -> None:
        """Append a Bedrock reasoning turn."""
        with (self._cache_root / "ai" / "reasoning.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def write_rca(self, content: str) -> None:
        """Write the final root cause analysis markdown."""
        (self._cache_root / "ai" / "rca.md").write_text(content, encoding="utf-8")

    def write_artifact(self, filename: str, content: bytes | str) -> None:
        """Write an artifact file to the session artifacts directory."""
        path = self._cache_root / "artifacts" / filename
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)

    # ── Completion ────────────────────────────────────────────────────────────

    def complete(self, status: str, summary: dict[str, Any]) -> None:
        """Mark session as complete, write summary.json, flush all to S3."""
        self.status = status
        completed_at = datetime.now(UTC)

        meta_path = self._cache_root / "session.json"
        meta = json.loads(meta_path.read_text())
        meta["status"] = status
        meta["completed_at"] = completed_at.isoformat()
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        (self._cache_root / "summary.json").write_text(
            json.dumps({**summary, "session_id": self.session_id}, indent=2),
            encoding="utf-8",
        )
        print(f"[session] Completed {self.session_id} status={status}", flush=True)
        self._flush_to_s3()

    def _s3_key(self, relative: str) -> str:
        prefix = settings.s3_prefix.rstrip("/")
        return f"{prefix}/{settings.github_repo}/{self.commit_short}/{relative}"

    def _ensure_bucket(self, s3: Any) -> None:
        """Create the S3 bucket if it doesn't already exist."""
        try:
            s3.head_bucket(Bucket=settings.s3_bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchBucket"):
                try:
                    if settings.s3_region == "us-east-1":
                        s3.create_bucket(Bucket=settings.s3_bucket)
                    else:
                        s3.create_bucket(
                            Bucket=settings.s3_bucket,
                            CreateBucketConfiguration={"LocationConstraint": settings.s3_region},
                        )
                    print(f"[session] Created S3 bucket: {settings.s3_bucket}", flush=True)
                except ClientError as create_exc:
                    print(f"[session] Could not create bucket: {create_exc}", flush=True)

    def _flush_to_s3(self) -> None:
        """Upload all local cache files to S3."""
        s3_kwargs: dict[str, Any] = {"region_name": settings.s3_region}
        if settings.aws_endpoint_url:
            s3_kwargs["endpoint_url"] = settings.aws_endpoint_url
        s3 = boto3.client("s3", **s3_kwargs)

        self._ensure_bucket(s3)

        uploaded = 0
        for file_path in self._cache_root.rglob("*"):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(self._cache_root).as_posix()
            key = self._s3_key(relative)
            try:
                s3.upload_file(str(file_path), settings.s3_bucket, key)
                uploaded += 1
            except ClientError as exc:
                print(f"[session] S3 upload failed for {relative}: {exc}", flush=True)

        s3_path = f"s3://{settings.s3_bucket}/{self._s3_key('')}"
        print(f"[session] Flushed {uploaded} file(s) to {s3_path}", flush=True)
