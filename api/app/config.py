from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+asyncpg://sre_agent:sre_agent@localhost:5432/sre_agent"
    ingest_api_key: str = "devkey"
    ingest_auth_disabled: bool = False
    artifacts_dir: str = "/data/artifacts"
    cors_origins: str = "http://localhost:3000"


settings = Settings()

