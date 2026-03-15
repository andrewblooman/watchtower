from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

DATABASE_URL_ASYNC = settings.database_url
if "+asyncpg" in DATABASE_URL_ASYNC:
    DATABASE_URL_SYNC = DATABASE_URL_ASYNC.replace("postgresql+asyncpg://", "postgresql+psycopg://")
else:
    DATABASE_URL_SYNC = DATABASE_URL_ASYNC

engine: AsyncEngine = create_async_engine(DATABASE_URL_ASYNC, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
