"""Local development stubs — activated when LOCAL_DEV=true.

Replaces real CloudWatch/ECS and Bedrock calls with:
  - LocalAWSClient: reads *.log files from SAMPLE_DATA_DIR/logs/
  - LocalBedrockClient: returns canned-but-realistic responses (no AWS calls)

S3 flush still runs against LocalStack, so the full pipeline executes.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.config import settings
from agent.session import InvestigationSession


class LocalAWSClient:
    """Reads *.log files from SAMPLE_DATA_DIR in place of real CloudWatch/ECS APIs."""

    def _log_dir(self) -> Path:
        return Path(settings.sample_data_dir) / "logs"

    def find_log_groups(self, prefix: str | None = None) -> list[str]:
        log_dir = self._log_dir()
        if not log_dir.is_dir():
            print(f"[local] sample-data dir not found: {log_dir}", flush=True)
            return []
        groups = [f.stem for f in sorted(log_dir.glob("*.log"))]
        print(f"[local] Found {len(groups)} local log file(s): {groups}", flush=True)
        return groups

    def get_log_events(
        self,
        log_group: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        filter_pattern: str = "",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        path = self._log_dir() / f"{log_group}.log"
        if not path.exists():
            print(f"[local] Log file not found: {path}", flush=True)
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^(\d{4}-\d{2}-\d{2}T[\d:Z]+)\s+(.*)", line)
            ts, msg = (m.group(1), m.group(2)) if m else (datetime.now(UTC).isoformat(), line)
            if filter_pattern and filter_pattern.lower() not in line.lower():
                continue
            events.append({"ts": ts, "message": msg, "log_stream": "local"})
            if limit and len(events) >= limit:
                break
        return events

    def describe_ecs_service(self, cluster: str, service: str) -> dict[str, Any] | None:
        # Simulate a degraded service — 1 of 2 desired tasks running
        return {
            "serviceName": service,
            "clusterArn": f"arn:aws:ecs:us-east-1:123456789012:cluster/{cluster}",
            "status": "ACTIVE",
            "desiredCount": 2,
            "runningCount": 1,
            "pendingCount": 0,
            "deployments": [
                {"status": "PRIMARY", "desiredCount": 2, "runningCount": 1, "failedTasks": 1}
            ],
        }

    def list_ecs_tasks(self, cluster: str, service: str | None = None) -> list[str]:
        return ["arn:aws:ecs:us-east-1:123456789012:task/local-task-1"]

    def get_metric_statistics(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []


class LocalBedrockClient:
    """Canned Bedrock responses for local dev — no real AWS credentials required."""

    def __init__(self, session: InvestigationSession) -> None:
        self._session = session
        self._turn = 0

    def analyze(self, context: str, prompt_summary: str) -> dict[str, Any]:
        self._turn += 1
        ts = datetime.now(UTC).isoformat()

        # Scan context for error/warn lines to build a realistic-looking response
        errors = re.findall(r"ERROR[^\n]*", context)
        error_bullets = "\n".join(f"- {e.strip()}" for e in errors[:5]) or "- No errors found"

        response_text = (
            f"## Analysis (Turn {self._turn}) -- LOCAL DEV STUB\n\n"
            "### Observed Issues\n"
            f"{error_bullets}\n\n"
            "### Root Cause\n"
            "The payment-api service failed to authenticate with the database "
            "(DB_AUTH_FAILED) shortly after deployment, causing the frontend-app to "
            "receive HTTP 504 Gateway Timeout responses. The ECS service shows only 1 of "
            "2 desired tasks running, indicating incomplete recovery after credential "
            "rotation.\n\n"
            "### Recommendation\n"
            "1. Verify all payment-api ECS tasks are healthy post-rotation.\n"
            "2. Investigate whether DB credentials in Secrets Manager were updated "
            "before or after deployment.\n"
            "3. Add an ECS container health-check that validates DB connectivity on "
            "startup to prevent tasks from entering RUNNING state prematurely.\n\n"
            "Confidence: 0.87"
        )

        record = {
            "ts": ts,
            "turn": self._turn,
            "model": "local-stub",
            "prompt_tokens": len(context.split()),
            "completion_tokens": len(response_text.split()),
            "prompt_summary": prompt_summary,
            "response": response_text,
        }
        self._session.append_reasoning(record)
        print(f"[local-bedrock] Turn {self._turn}: {prompt_summary[:70]}", flush=True)
        return {"success": True, "response": response_text, "turn": self._turn}

    def generate_rca(self, investigation_context: str) -> str:
        self.analyze(investigation_context, "Generating final RCA document")
        return (
            "# Root Cause Analysis\n\n"
            f"**Repository:** {settings.github_repo}  \n"
            f"**Commit:** {settings.commit_sha[:7]}  \n"
            f"**Service:** {settings.service_name}  \n"
            f"**Environment:** {settings.environment}  \n\n"
            "## Summary\n"
            "The payment-api service failed to authenticate with the database immediately "
            "after deployment, causing cascading 504 errors in frontend-app and leaving "
            "the ECS service in a degraded state (1/2 tasks running).\n\n"
            "## Root Cause\n"
            "Database credentials referenced by the service were rotated or had expired "
            "(error code: DB_AUTH_FAILED). The running service was not notified of "
            "updated credentials, causing all DB connections to fail on startup.\n\n"
            "## Impact\n"
            "- **frontend-app**: HTTP 504 Gateway Timeout for all payment flows\n"
            "- **payment-api**: authentication failures; ECS task count degraded (1/2)\n\n"
            "## Timeline\n"
            "- `22:20:01Z` — payment-api deployed, service started\n"
            "- `22:21:42Z` — DB_AUTH_FAILED error detected\n"
            "- `22:22:07Z` — Elevated 5xx rate on payment-api\n"
            "- `22:23:10Z` — Credentials rotated, DB connection restored\n"
            "- `22:24:09Z` — frontend-app still receiving upstream timeouts\n\n"
            "## Remediation Steps\n"
            "1. Force a new deployment to replace the degraded task with fresh credentials.\n"
            "2. Verify Secrets Manager rotation updated the value before deployment ran.\n"
            "3. Add a DB connectivity check to the ECS container health-check command.\n\n"
            "## Prevention\n"
            "- Automate Secrets Manager rotation with Lambda notification to ECS.\n"
            "- Implement circuit breaker in frontend-app for the payment-api dependency.\n"
            "- Add pre-deployment smoke test that validates DB credentials are reachable.\n"
        )

    def extract_diagnosis(self, response_text: str) -> dict[str, Any]:
        confidence = 0.5
        m = re.search(r"[Cc]onfidence[:\s]+([0-9]+(?:\.[0-9]+)?)", response_text)
        if m:
            try:
                confidence = max(0.0, min(1.0, float(m.group(1))))
            except ValueError:
                pass
        return {
            "root_cause": response_text[:500],
            "confidence": confidence,
            "recommendation": "See full RCA document for remediation steps.",
        }
