"""
Database connection model with encrypted credentials.

Design principles:
- Only metadata is stored (host, port, db name, db type).
- Actual credentials (username, password) are stored AES-256 encrypted.
- The application never copies customer business data into its own database.
- Each connection can be tested independently before use.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.schema_metadata import SchemaMetadata
    from app.models.table_permission import TablePermission
    from app.models.column_permission import ColumnPermission
    from app.models.row_filter import RowFilter
    from app.models.conversation import Conversation
    from app.models.query_log import QueryLog


class DatabaseConnection(Base, AuditableMixin):
    """
    Runtime database connection registered by a tenant admin.

    The db_type determines which adapter is used at query time.
    Credentials are encrypted with Fernet before insertion and
    decrypted on demand — they are never logged or exposed in API responses.
    """

    __tablename__ = "database_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_db_connections_tenant_name"),
        CheckConstraint(
            "db_type IN ('postgresql', 'mysql', 'sqlserver', 'oracle')",
            name="ck_db_connections_type",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    db_type: Mapped[str] = mapped_column(String(20), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Encrypted JSON blob: {"username": "enc...", "password": "enc..."}
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    # Additional connection options (SSL mode, charset, etc.)
    connection_options: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Last successful connection test timestamp
    last_tested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_schema_sync_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="database_connections")
    schema_metadata: Mapped[list["SchemaMetadata"]] = relationship(
        "SchemaMetadata", back_populates="connection", cascade="all, delete-orphan"
    )
    table_permissions: Mapped[list["TablePermission"]] = relationship(
        "TablePermission", back_populates="connection", cascade="all, delete-orphan"
    )
    column_permissions: Mapped[list["ColumnPermission"]] = relationship(
        "ColumnPermission", back_populates="connection", cascade="all, delete-orphan"
    )
    row_filters: Mapped[list["RowFilter"]] = relationship(
        "RowFilter", back_populates="connection", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="connection"
    )
    query_logs: Mapped[list["QueryLog"]] = relationship(
        "QueryLog", back_populates="connection"
    )

    def __repr__(self) -> str:
        return (
            f"<DatabaseConnection id={self.id} name={self.name!r} "
            f"type={self.db_type} tenant={self.tenant_id}>"
        )
