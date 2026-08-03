"""User repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email_and_tenant(
        self, email: str, tenant_id: uuid.UUID
    ) -> User | None:
        """Fetch a user by email within a specific tenant."""
        stmt = (
            select(User)
            .where(User.email == email.lower(), User.tenant_id == tenant_id)
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user with roles eagerly loaded."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_id_and_tenant(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> User | None:
        """Fetch an active user by ID within a tenant."""
        stmt = (
            select(User)
            .where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
            )
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists_in_tenant(
        self, email: str, tenant_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None
    ) -> bool:
        """Check if an email is already taken within a tenant."""
        stmt = select(User.id).where(
            User.email == email.lower(), User.tenant_id == tenant_id
        )
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
