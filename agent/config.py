from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Deployment identity  injected from EventBridge via ECS task env vars
    github_repo: str = "unknown/unknown"  # e.g. "org/my-service"
    commit_sha: str = "0000000000000000000000000000000000000000"
    service_name: str = "unknown"
    environment: str = "production"

    # S3 storage
    s3_bucket: str = "sre-agent-investigations"
    s3_prefix: str = "investigations"
    s3_region: str = "us-east-1"
    aws_endpoint_url: str | None = None  # For LocalStack local dev

    # Amazon Bedrock
    bedrock_region: str = "us-east-1"
    bedrock_endpoint_url: str | None = None
    bedrock_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # Local ephemeral cache
    cache_dir: str = "/data/cache"
    cache_ttl_hours: int = 6

    # Investigation limits
    investigation_timeout_minutes: int = 30
    max_reasoning_turns: int = 10

    # CloudWatch
    cloudwatch_log_lookback_minutes: int = 30
    cloudwatch_max_events: int = 1000

    # ECS cluster naming (defaults to {environment}-cluster)
    ecs_cluster: str = ""

    # Local development mode — reads sample-data instead of calling real AWS APIs
    local_dev: bool = False
    sample_data_dir: str = "/app/sample-data"


settings = Settings()
