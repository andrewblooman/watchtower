"""AWS API wrappers: CloudWatch Logs, ECS, CloudWatch Metrics."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import boto3

from agent.config import settings


def _client(service: str):
    kwargs: dict[str, Any] = {"region_name": settings.s3_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client(service, **kwargs)


class AWSClient:
    """Thin wrappers around CloudWatch Logs, ECS, and CloudWatch Metrics."""

    def find_log_groups(self, prefix: str | None = None) -> list[str]:
        """List CloudWatch log group names, optionally filtered by prefix."""
        cw = _client("logs")
        kwargs: dict[str, Any] = {}
        if prefix:
            kwargs["logGroupNamePrefix"] = prefix
        paginator = cw.get_paginator("describe_log_groups")
        groups: list[str] = []
        try:
            for page in paginator.paginate(**kwargs):
                for g in page.get("logGroups", []):
                    groups.append(g["logGroupName"])
        except Exception as exc:
            print(f"[aws] describe_log_groups error: {exc}", flush=True)
        return groups

    def get_log_events(
        self,
        log_group: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        filter_pattern: str = "",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent log events from a CloudWatch log group."""
        cw = _client("logs")
        if start_time is None:
            start_time = datetime.now(UTC) - timedelta(
                minutes=settings.cloudwatch_log_lookback_minutes
            )
        if end_time is None:
            end_time = datetime.now(UTC)
        max_events = limit or settings.cloudwatch_max_events
        kwargs: dict[str, Any] = {
            "logGroupName": log_group,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": min(max_events, 10000),
        }
        if filter_pattern:
            kwargs["filterPattern"] = filter_pattern
        events: list[dict[str, Any]] = []
        try:
            paginator = cw.get_paginator("filter_log_events")
            for page in paginator.paginate(**kwargs):
                for e in page.get("events", []):
                    events.append(
                        {
                            "ts": datetime.fromtimestamp(
                                e["timestamp"] / 1000, tz=UTC
                            ).isoformat(),
                            "message": e.get("message", ""),
                            "log_stream": e.get("logStreamName", ""),
                        }
                    )
                    if len(events) >= max_events:
                        return events
        except Exception as exc:
            print(f"[aws] filter_log_events error ({log_group}): {exc}", flush=True)
        return events

    def describe_ecs_service(self, cluster: str, service: str) -> dict[str, Any] | None:
        """Return ECS service description or None on error."""
        ecs = _client("ecs")
        try:
            resp = ecs.describe_services(cluster=cluster, services=[service])
            services = resp.get("services", [])
            return services[0] if services else None
        except Exception as exc:
            print(f"[aws] describe_services error ({cluster}/{service}): {exc}", flush=True)
            return None

    def list_ecs_tasks(self, cluster: str, service: str | None = None) -> list[str]:
        """List ECS task ARNs in a cluster, optionally scoped to a service."""
        ecs = _client("ecs")
        kwargs: dict[str, Any] = {"cluster": cluster}
        if service:
            kwargs["serviceName"] = service
        try:
            return ecs.list_tasks(**kwargs).get("taskArns", [])
        except Exception as exc:
            print(f"[aws] list_tasks error: {exc}", flush=True)
            return []

    def get_metric_statistics(
        self,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        period: int = 300,
        stat: str = "Average",
        minutes_back: int = 30,
    ) -> list[dict[str, Any]]:
        """Return CloudWatch metric data points sorted by time."""
        cw = _client("cloudwatch")
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=minutes_back)
        try:
            resp = cw.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[stat],
            )
            return sorted(
                [
                    {"ts": dp["Timestamp"].isoformat(), "value": dp[stat]}
                    for dp in resp.get("Datapoints", [])
                ],
                key=lambda x: x["ts"],
            )
        except Exception as exc:
            print(f"[aws] get_metric_statistics error ({namespace}/{metric_name}): {exc}", flush=True)
            return []
