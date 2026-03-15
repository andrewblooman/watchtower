from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    api_base: str = "http://localhost:8000"
    ingest_api_key: str = "devkey"
    mode: str = "persistent"  # persistent | oneshot
    interval_seconds: int = 10
    logs_dir: str = "/sample-data/logs"
    artifacts_dir: str = "/data/artifacts"
    tenant_name: str = "Acme Corp"


settings = Settings()

