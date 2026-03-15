from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.ingest import IngestClient


SERVICE_RE = re.compile(r"service=(?P<service>[a-zA-Z0-9_-]+)")
ENV_RE = re.compile(r"env=(?P<env>[a-zA-Z0-9_-]+)")


@dataclass
class ScopeState:
    run_id: str | None = None
    incident_id: str | None = None
    last_error_at: datetime | None = None


class Simulator:
    def __init__(self, client: IngestClient, *, tenant: str, artifacts_dir: str):
        self._client = client
        self._tenant = tenant
        self._artifacts_dir = Path(artifacts_dir)
        self._state: dict[tuple[str, str], ScopeState] = {}

    def _scope_state(self, service: str, env: str) -> ScopeState:
        key = (service, env)
        if key not in self._state:
            self._state[key] = ScopeState()
        return self._state[key]

    def _ensure_run(self, service: str, env: str, version: str | None = None) -> str:
        st = self._scope_state(service, env)
        if st.run_id:
            return st.run_id
        resp = self._client.ingest_event(
            tenant=self._tenant,
            service=service,
            environment=env,
            version=version,
            event_type="deployment_started",
            message=f"Deployment observed for {service} ({env})",
            meta={"source": "sim"},
        )
        st.run_id = resp["run_id"]
        st.incident_id = resp.get("incident_id")
        return st.run_id

    def _write_artifact(self, rel_path: str, content: dict[str, Any]) -> str:
        p = (self._artifacts_dir / rel_path).resolve()
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(content, indent=2), encoding="utf-8")
        return rel_path

    def _emit_test_suite(self, service: str, env: str, suite: str, should_fail: bool) -> None:
        st = self._scope_state(service, env)
        run_id = self._ensure_run(service, env)
        now = datetime.now(UTC)
        self._client.ingest_event(
            tenant=self._tenant,
            service=service,
            environment=env,
            run_id=run_id,
            incident_id=st.incident_id,
            event_type="test_started",
            message=f"{suite} tests started",
            ts=now,
            meta={"suite": suite, "source": "sim"},
        )

        duration_ms = random.randint(400, 2200)
        outcome = "failed" if should_fail else "passed"
        event_type = "test_failed" if should_fail else "test_passed"
        artifact_rel = self._write_artifact(
            f"tests/{service}-{env}-{suite}-results.json",
            {
                "suite": suite,
                "service": service,
                "environment": env,
                "outcome": outcome,
                "duration_ms": duration_ms,
                "sample_output": "HTTP 500" if should_fail else "OK",
                "ts": now.isoformat(),
            },
        )
        resp = self._client.ingest_event(
            tenant=self._tenant,
            service=service,
            environment=env,
            run_id=run_id,
            incident_id=st.incident_id,
            event_type=event_type,
            message=f"{suite} tests {outcome}",
            ts=datetime.now(UTC),
            meta={
                "suite": suite,
                "duration_ms": duration_ms,
                "source": "sim",
                "artifacts": [
                    {"kind": "tests", "name": f"{suite} results", "path_or_url": artifact_rel},
                ],
                "title": f"{suite} test {outcome}".title(),
            },
        )
        st.incident_id = resp.get("incident_id") or st.incident_id

    def handle_log_line(self, line: str) -> None:
        service_m = SERVICE_RE.search(line)
        env_m = ENV_RE.search(line)
        if not service_m or not env_m:
            return

        service = service_m.group("service")
        env = env_m.group("env")
        st = self._scope_state(service, env)
        run_id = self._ensure_run(service, env)
        now = datetime.now(UTC)

        if "ERROR" in line or "Exception" in line:
            st.last_error_at = now
            resp = self._client.ingest_event(
                tenant=self._tenant,
                service=service,
                environment=env,
                run_id=run_id,
                incident_id=st.incident_id,
                event_type="log_detected",
                message=line,
                ts=now,
                meta={
                    "source": "log-tail",
                    "title": "Log error detected",
                },
            )
            st.incident_id = resp.get("incident_id") or st.incident_id

            rca = {
                "root_cause_summary": "Database authentication failure",
                "confidence": 0.92,
                "suggested_action": "Rollback deployment",
                "source": "sim-llm",
            }
            self._client.ingest_event(
                tenant=self._tenant,
                service=service,
                environment=env,
                run_id=run_id,
                incident_id=st.incident_id,
                event_type="recommendation",
                message="AI diagnosis produced a rollback recommendation",
                ts=datetime.now(UTC),
                meta=rca,
            )
            self._client.ingest_event(
                tenant=self._tenant,
                service=service,
                environment=env,
                run_id=run_id,
                incident_id=st.incident_id,
                event_type="slack_sent",
                message=f"Slack: Incident alert for {service} ({env})",
                ts=datetime.now(UTC),
                meta={"channel": "#sre-alerts", "source": "sim"},
            )

            self._emit_test_suite(service, env, "unit", should_fail=False)
            self._emit_test_suite(service, env, "smoke", should_fail=True)
            self._client.ingest_event(
                tenant=self._tenant,
                service=service,
                environment=env,
                run_id=run_id,
                incident_id=st.incident_id,
                event_type="rollback_started",
                message="Rollback initiated due to failing smoke tests",
                ts=datetime.now(UTC),
                meta={"source": "sim", "open_incident": True},
            )
            return

        if "RECOVERY:" in line or "RECOVERED" in line:
            self._client.ingest_event(
                tenant=self._tenant,
                service=service,
                environment=env,
                run_id=run_id,
                incident_id=st.incident_id,
                event_type="recovery_detected",
                message=line,
                ts=now,
                meta={"source": "log-tail", "resolve_incident": True},
            )
            st.incident_id = None
            st.run_id = None
            return

        self._client.ingest_event(
            tenant=self._tenant,
            service=service,
            environment=env,
            run_id=run_id,
            incident_id=st.incident_id,
            event_type="log_observed",
            message=line,
            ts=now,
            meta={"source": "log-tail"},
        )

