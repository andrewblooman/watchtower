from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import settings


def require_ingest_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")) -> None:
    if settings.ingest_auth_disabled:
        return
    if not x_api_key or x_api_key != settings.ingest_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-Api-Key")

