"""Repositories for security permissions (TablePermission, ColumnPermission, RowFilter)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.column_permission import ColumnPermission
from app.models.row_filter import RowFilter
from app.models.table_permission import TablePermission
from app.repositories.base import BaseRepository


class TablePermissionRepository(BaseRepository[TablePermission]):
    """Repository for table-level security permissions."""

    model = TablePermission

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_for_roles_and_connection(
        self, role_ids: list[uuid.UUID], connection_id: uuid.UUID
    ) -> Sequence[TablePermission]:
        """Fetch all table permission rules for given roles and connection."""
        if not role_ids:
            return []
        stmt = select(TablePermission).where(
            TablePermission.role_id.in_(role_ids),
            TablePermission.connection_id == connection_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ColumnPermissionRepository(BaseRepository[ColumnPermission]):
    """Repository for column-level security permissions."""

    model = ColumnPermission

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_for_roles_and_connection(
        self, role_ids: list[uuid.UUID], connection_id: uuid.UUID
    ) -> Sequence[ColumnPermission]:
        """Fetch column permission rules for given roles and connection."""
        if not role_ids:
            return []
        stmt = select(ColumnPermission).where(
            ColumnPermission.role_id.in_(role_ids),
            ColumnPermission.connection_id == connection_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class RowFilterRepository(BaseRepository[RowFilter]):
    """Repository for row-level security filters."""

    model = RowFilter

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_for_roles_and_connection(
        self, role_ids: list[uuid.UUID], connection_id: uuid.UUID
    ) -> Sequence[RowFilter]:
        """Fetch row filter rules for given roles and connection."""
        if not role_ids:
            return []
        stmt = select(RowFilter).where(
            RowFilter.role_id.in_(role_ids),
            RowFilter.connection_id == connection_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
