"""QueryLog and AuditLog repositories."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.query_log import QueryLog
from app.repositories.base import BaseRepository


class QueryLogRepository(BaseRepository[QueryLog]):
    """Repository for Text-to-SQL query execution logs."""

    model = QueryLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[QueryLog]:
        """List query logs for tenant."""
        stmt = (
            select(QueryLog)
            .where(QueryLog.tenant_id == tenant_id)
            .order_by(QueryLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for security audit logs."""

    model = AuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[AuditLog]:
        """List audit logs for tenant."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
