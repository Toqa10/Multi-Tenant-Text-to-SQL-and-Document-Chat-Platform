"""Database Connection & Schema Management Service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import DatabaseAdapterFactory
from app.core.encryption import decrypt_dict, encrypt_dict
from app.core.exceptions import NotFoundError
from app.models.database_connection import DatabaseConnection
from app.models.schema_metadata import SchemaMetadata
from app.repositories.database_connection import DatabaseConnectionRepository
from app.repositories.schema_metadata import SchemaMetadataRepository
from app.schemas.connection import DatabaseConnectionCreate, DatabaseConnectionUpdate


class ConnectionService:
    """Service for managing database connections, credential encryption, testing, and schema discovery."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conn_repo = DatabaseConnectionRepository(session)
        self.schema_repo = SchemaMetadataRepository(session)

    async def create_connection(
        self, tenant_id: uuid.UUID, req: DatabaseConnectionCreate
    ) -> DatabaseConnection:
        """Encrypt credentials and save database connection metadata."""
        creds_json = json.dumps({"username": req.username, "password": req.password})
        encrypted_creds = encrypt_dict({"credentials": creds_json})["credentials"]

        conn = await self.conn_repo.create(
            tenant_id=tenant_id,
            name=req.name,
            description=req.description,
            db_type=req.db_type,
            host=req.host,
            port=req.port,
            database_name=req.database_name,
            encrypted_credentials=encrypted_creds,
            connection_options=req.connection_options,
            is_active=True,
        )
        return conn

    async def get_adapter_for_connection(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ):
        """Decrypt credentials and return configured BaseDatabaseAdapter."""
        conn = await self.conn_repo.get_by_id_and_tenant(connection_id, tenant_id)
        if not conn:
            raise NotFoundError(message="Database connection not found.")

        decrypted_json = decrypt_dict({"credentials": conn.encrypted_credentials})["credentials"]
        creds = json.loads(decrypted_json)

        return DatabaseAdapterFactory.get_adapter(
            db_type=conn.db_type,
            host=conn.host,
            port=conn.port,
            database=conn.database_name,
            username=creds["username"],
            password=creds["password"],
            options=conn.connection_options,
        )

    async def test_connection(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> tuple[bool, float, str]:
        """Test connection latency and status."""
        adapter = await self.get_adapter_for_connection(connection_id, tenant_id)
        success, latency, msg = await adapter.test_connection()

        if success:
            conn = await self.conn_repo.get_by_id_and_tenant(connection_id, tenant_id)
            if conn:
                conn.last_tested_at = datetime.now(UTC)
                await self.session.flush()

        return success, latency, msg

    async def sync_schema(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Introspect database schema and update cached SchemaMetadata."""
        adapter = await self.get_adapter_for_connection(connection_id, tenant_id)
        columns_info = await adapter.discover_schema()

        # Clear existing cached schema for this connection
        await self.schema_repo.delete_by_connection(connection_id)

        # Bulk insert new column metadata
        for col in columns_info:
            await self.schema_repo.create(
                connection_id=connection_id,
                schema_name=col.schema_name,
                table_name=col.table_name,
                table_comment=col.table_comment,
                column_name=col.column_name,
                column_comment=col.column_comment,
                data_type=col.data_type,
                is_nullable=col.is_nullable,
                ordinal_position=col.ordinal_position,
                is_primary_key=col.is_primary_key,
                is_foreign_key=col.is_foreign_key,
                foreign_table=col.foreign_table,
                foreign_column=col.foreign_column,
            )

        conn = await self.conn_repo.get_by_id_and_tenant(connection_id, tenant_id)
        if conn:
            conn.last_schema_sync_at = datetime.now(UTC)
            await self.session.flush()

        return len(columns_info)

    async def get_schema_metadata(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Sequence[SchemaMetadata]:
        """Retrieve cached schema metadata."""
        conn = await self.conn_repo.get_by_id_and_tenant(connection_id, tenant_id)
        if not conn:
            raise NotFoundError(message="Database connection not found.")
        return await self.schema_repo.get_by_connection(connection_id)
