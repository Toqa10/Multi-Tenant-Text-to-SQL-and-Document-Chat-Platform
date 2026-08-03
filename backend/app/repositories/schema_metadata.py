"""SchemaMetadata repository."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema_metadata import SchemaMetadata
from app.repositories.base import BaseRepository


class SchemaMetadataRepository(BaseRepository[SchemaMetadata]):
    """Repository for cached database schema metadata."""

    model = SchemaMetadata

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_connection(
        self, connection_id: uuid.UUID
    ) -> Sequence[SchemaMetadata]:
        """Fetch all column metadata for a database connection."""
        stmt = (
            select(SchemaMetadata)
            .where(SchemaMetadata.connection_id == connection_id)
            .order_by(
                SchemaMetadata.schema_name,
                SchemaMetadata.table_name,
                SchemaMetadata.ordinal_position,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_tables(
        self, connection_id: uuid.UUID
    ) -> Sequence[str]:
        """List unique table names in a database connection."""
        stmt = (
            select(SchemaMetadata.table_name)
            .where(SchemaMetadata.connection_id == connection_id)
            .distinct()
            .order_by(SchemaMetadata.table_name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_connection(self, connection_id: uuid.UUID) -> int:
        """Clear all cached schema metadata for a connection prior to resync."""
        stmt = sa_delete(SchemaMetadata).where(
            SchemaMetadata.connection_id == connection_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
