from __future__ import annotations

import time

from agent.config import settings
from agent.ingest import IngestClient
from agent.log_tail import LogTailer
from agent.sim import Simulator


def run_once() -> None:
    client = IngestClient(settings.api_base, settings.ingest_api_key)
    tailer = LogTailer(settings.logs_dir)
    sim = Simulator(client, tenant=settings.tenant_name, artifacts_dir=settings.artifacts_dir)

    lines = tailer.poll()
    for ll in lines:
        sim.handle_log_line(ll.line)


def main() -> None:
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[agent] cycle failed: {e}", flush=True)
        if settings.mode.lower() == "oneshot":
            return
        time.sleep(max(1, settings.interval_seconds))


if __name__ == "__main__":
    main()
