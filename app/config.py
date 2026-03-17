from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # S3 storage
    s3_bucket: str = "sre-agent-investigations"
    s3_prefix: str = "investigations"
    s3_region: str = "us-east-1"
    aws_endpoint_url: str | None = None  # For LocalStack local dev

    # Local ephemeral cache
    cache_dir: str = "/data/cache"
    cache_ttl_hours: int = 6


settings = Settings()

