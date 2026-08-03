"""Tenant repository."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant model operations."""

    model = Tenant

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Fetch tenant by slug."""
        stmt = select(Tenant).where(Tenant.slug == slug.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, offset: int = 0, limit: int = 50
    ) -> Sequence[Tenant]:
        """List all tenants with pagination."""
        stmt = select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
