"""Role and Permission repository."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role, RolePermission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for Role model operations."""

    model = Role

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_name_and_tenant(
        self, name: str, tenant_id: uuid.UUID
    ) -> Role | None:
        """Fetch role by name and tenant_id."""
        stmt = (
            select(Role)
            .where(Role.name == name, Role.tenant_id == tenant_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(
        self, role_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Role | None:
        """Fetch role by ID with permissions eagerly loaded."""
        stmt = (
            select(Role)
            .where(Role.id == role_id, Role.tenant_id == tenant_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    """Repository for atomic Permission operations."""

    model = Permission

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_resource_and_action(
        self, resource: str, action: str
    ) -> Permission | None:
        """Fetch permission by resource and action."""
        stmt = select(Permission).where(
            Permission.resource == resource, Permission.action == action
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Permission]:
        """List all defined platform permissions."""
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        result = await self.session.execute(stmt)
        return result.scalars().all()
