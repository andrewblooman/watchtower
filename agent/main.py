"""SRE debugging agent  event-driven, short-lived ECS investigation task."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from agent.aws_client import AWSClient
from agent.bedrock import BedrockClient
from agent.command_runner import CommandRunner
from agent.config import settings
from agent.session import InvestigationSession


def _ecs_cluster() -> str:
    return settings.ecs_cluster or f"{settings.environment}-cluster"


def _build_context(
    logs_by_group: dict[str, list[dict[str, Any]]],
    ecs_status: dict[str, Any] | None,
) -> str:
    """Assemble an investigation context string for Bedrock."""
    parts = [
        "# Investigation Context",
        f"Repository: {settings.github_repo}",
        f"Commit: {settings.commit_sha[:7]}",
        f"Service: {settings.service_name}",
        f"Environment: {settings.environment}",
        f"Timestamp: {datetime.now(UTC).isoformat()}",
        "",
    ]
    if ecs_status:
        parts += [
            "## ECS Service Status",
            f"Desired count: {ecs_status.get('desiredCount', 'N/A')}",
            f"Running count: {ecs_status.get('runningCount', 'N/A')}",
            f"Status: {ecs_status.get('status', 'N/A')}",
            "",
        ]
    for group, events in logs_by_group.items():
        if not events:
            continue
        parts += [f"## CloudWatch Logs: {group}", f"({len(events)} events)"]
        for e in events[-50:]:  # last 50 lines to stay within token limits
            parts.append(f"[{e.get('ts', '')}] {e.get('message', '').strip()}")
        parts.append("")
    return "\n".join(parts)


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open(encoding="utf-8"))
    except Exception:
        return 0


def run_investigation() -> None:
    session = InvestigationSession()
    runner = CommandRunner(session)
    timeout_at = datetime.now(UTC) + timedelta(minutes=settings.investigation_timeout_minutes)

    if settings.local_dev:
        from agent.local_dev import LocalAWSClient, LocalBedrockClient

        aws: AWSClient = LocalAWSClient()  # type: ignore[assignment]
        bedrock: BedrockClient = LocalBedrockClient(session)  # type: ignore[assignment]
        print("[agent] LOCAL DEV MODE — using sample-data logs and stub Bedrock client", flush=True)
    else:
        aws = AWSClient()
        bedrock = BedrockClient(session)

    print(
        f"[agent] Investigating {settings.github_repo}@{settings.commit_sha[:7]} "
        f"({settings.service_name}/{settings.environment})",
        flush=True,
    )

    # Phase 1: Gather CloudWatch logs
    print("[agent] Phase 1: Fetching CloudWatch logs...", flush=True)
    log_prefix = f"/{settings.environment}/{settings.service_name}"
    log_groups = aws.find_log_groups(prefix=log_prefix)
    if not log_groups:
        log_groups = aws.find_log_groups(prefix=f"/ecs/{settings.service_name}")
    runner.record_tool("cloudwatch:describe_log_groups", {"prefix": log_prefix}, log_groups)

    logs_by_group: dict[str, list[dict[str, Any]]] = {}
    for group in log_groups[:5]:
        events = aws.get_log_events(group)
        runner.record_tool(
            "cloudwatch:filter_log_events",
            {"log_group": group, "limit": settings.cloudwatch_max_events},
            {"event_count": len(events)},
        )
        logs_by_group[group] = events
        session.append_log(group, events)
        print(f"[agent]   {group}: {len(events)} events", flush=True)

    # Phase 2: Check ECS service status
    print("[agent] Phase 2: Checking ECS service status...", flush=True)
    cluster = _ecs_cluster()
    ecs_status = aws.describe_ecs_service(cluster, settings.service_name)
    runner.record_tool(
        "ecs:describe_services",
        {"cluster": cluster, "service": settings.service_name},
        ecs_status,
    )

    # Phase 3: Initial Bedrock analysis
    print("[agent] Phase 3: Initial Bedrock analysis...", flush=True)
    context = _build_context(logs_by_group, ecs_status)
    result = bedrock.analyze(
        context,
        f"Initial analysis of {settings.service_name}@{settings.commit_sha[:7]}",
    )
    diagnosis: dict[str, Any] = {}
    if result["success"]:
        diagnosis = bedrock.extract_diagnosis(result["response"])
        print(f"[agent] Confidence: {diagnosis.get('confidence', 0):.0%}", flush=True)

    # Phase 4: Follow-up reasoning if confidence is low
    turn = 1
    while (
        turn < settings.max_reasoning_turns
        and datetime.now(UTC) < timeout_at
        and diagnosis.get("confidence", 1.0) < 0.8
        and result.get("success")
    ):
        turn += 1
        print(f"[agent] Phase 4.{turn}: Follow-up analysis (low confidence)...", flush=True)
        follow_up = (
            f"Previous analysis:\n{result.get('response', '')}\n\n"
            f"Confidence is {diagnosis.get('confidence', 0):.0%}  too low. "
            "Look more carefully at error patterns and provide a more definitive diagnosis."
        )
        result = bedrock.analyze(follow_up, f"Follow-up reasoning turn {turn}")
        if result["success"]:
            diagnosis = bedrock.extract_diagnosis(result["response"])

    # Phase 5: Generate final RCA
    print("[agent] Phase 5: Generating RCA document...", flush=True)
    rca_content = bedrock.generate_rca(context)
    session.write_rca(rca_content)
    session.write_artifact("rca.md", rca_content)

    # Phase 6: Complete session and flush to S3
    cmd_file = session._cache_root / "commands" / "history.jsonl"
    summary: dict[str, Any] = {
        "root_cause": diagnosis.get("root_cause"),
        "confidence": diagnosis.get("confidence"),
        "recommendation": diagnosis.get("recommendation"),
        "commands_count": _count_lines(cmd_file),
        "reasoning_turns": bedrock._turn,
        "resolution": "resolved" if diagnosis.get("confidence", 0) >= 0.7 else "unresolved",
    }
    final_status = "timeout" if datetime.now(UTC) >= timeout_at else "resolved"
    session.complete(final_status, summary)
    print(f"[agent] Done. Session ID: {session.session_id}", flush=True)


def main() -> None:
    try:
        run_investigation()
    except KeyboardInterrupt:
        print("[agent] Interrupted.", flush=True)
        sys.exit(0)
    except Exception as exc:
        import traceback

        print(f"[agent] Investigation failed: {exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
