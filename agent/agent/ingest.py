from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class IngestClient:
    def __init__(self, api_base: str, api_key: str):
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key

    def ingest_event(
        self,
        *,
        tenant: str,
        service: str,
        environment: str,
        event_type: str,
        message: str,
        version: str | None = None,
        run_id: str | None = None,
        incident_id: str | None = None,
        ts: datetime | None = None,
        meta: dict[str, Any] | None = None,
        timeout_s: float = 10.0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenant": tenant,
            "service": service,
            "environment": environment,
            "version": version,
            "run_id": run_id,
            "incident_id": incident_id,
            "type": event_type,
            "ts": ts.isoformat().replace("+00:00", "Z") if ts else None,
            "message": message,
            "meta": meta or {},
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        resp = httpx.post(
            f"{self._api_base}/v1/ingest/event",
            headers={"X-Api-Key": self._api_key},
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        return resp.json()

