"""
Generic repository base class.

All repositories inherit from BaseRepository[ModelT].
Provides standard CRUD operations with tenant isolation enforcement.

Design:
- Repositories only talk to the database (no business logic).
- All list/get operations are tenant-scoped.
- Hard deletion is the default; soft-delete can be added per model.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository.

    Provides type-safe CRUD operations for any SQLAlchemy model.
    Tenant isolation is enforced by requiring tenant_id in all
    multi-tenant operations.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        """Fetch a record by primary key (no tenant filter)."""
        return await self.session.get(self.model, record_id)

    async def get_by_id_and_tenant(
        self, record_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ModelT | None:
        """Fetch a record by PK scoped to a specific tenant."""
        stmt = select(self.model).where(
            self.model.id == record_id,  # type: ignore[attr-defined]
            self.model.tenant_id == tenant_id,  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by: Any = None,
    ) -> list[ModelT]:
        """List all records for a tenant with pagination."""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id  # type: ignore[attr-defined]
        )
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        """Count all records for a tenant."""
        stmt = select(func.count()).select_from(self.model).where(
            self.model.tenant_id == tenant_id  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # Get the ID without committing
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        """Update an existing record's fields."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Hard-delete a record."""
        await self.session.delete(instance)
        await self.session.flush()

    async def delete_by_id(self, record_id: uuid.UUID) -> int:
        """Hard-delete by primary key. Returns number of deleted rows."""
        stmt = sa_delete(self.model).where(
            self.model.id == record_id  # type: ignore[attr-defined]
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def save(self, instance: ModelT) -> ModelT:
        """Merge and persist an instance (add or update)."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
