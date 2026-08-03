"""
Async SQLAlchemy 2.x database session management.

Architecture:
- One async engine per application process.
- AsyncSession is created per request and injected via FastAPI dependency.
- Sessions are scoped to the request lifecycle (committed on success, rolled
  back on exception, closed in a finally block).
- Alembic uses a separate SYNC engine to avoid event-loop conflicts during migrations.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()
_db = _settings.db


def _create_engine() -> AsyncEngine:
    """
    Create and configure the async SQLAlchemy engine.

    Engine options:
    - pool_pre_ping: Validate connections before reuse (handles DB restarts).
    - pool_size / max_overflow: Tunable via environment variables.
    - echo: Log SQL statements when DATABASE_ECHO=true (development only).
    """
    return create_async_engine(
        _db.async_url,
        pool_pre_ping=True,
        pool_size=_db.pool_size,
        max_overflow=_db.max_overflow,
        pool_timeout=_db.pool_timeout,
        echo=_db.echo,
        json_serializer=lambda obj: __import__("orjson").dumps(obj).decode(),
        json_deserializer=lambda s: __import__("orjson").loads(s),
    )


# Module-level engine and session factory (created once at import time)
engine: AsyncEngine = _create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides a database session.

    Commits on success, rolls back on exception.
    Intended for use in background tasks and Celery workers where
    FastAPI dependency injection is not available.

    Usage::

        async with get_db_context() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    Commits on success, rolls back on any unhandled exception.
    The session is always closed in the finally block.

    Usage in a FastAPI route::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
