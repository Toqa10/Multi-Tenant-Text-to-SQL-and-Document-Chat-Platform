"""DatabaseConnection repository."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_connection import DatabaseConnection
from app.repositories.base import BaseRepository


class DatabaseConnectionRepository(BaseRepository[DatabaseConnection]):
    """Repository for DatabaseConnection model operations."""

    model = DatabaseConnection

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_name_and_tenant(
        self, name: str, tenant_id: uuid.UUID
    ) -> DatabaseConnection | None:
        """Fetch database connection by name within tenant."""
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.name == name, DatabaseConnection.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> Sequence[DatabaseConnection]:
        """List active connections for a tenant."""
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.tenant_id == tenant_id,
            DatabaseConnection.is_active.is_(True),
        ).order_by(DatabaseConnection.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()
