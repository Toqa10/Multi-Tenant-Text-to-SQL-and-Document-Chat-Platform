"""Schema metadata model — cached introspection of customer databases."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.database_connection import DatabaseConnection


class SchemaMetadata(Base, AuditableMixin):
    """
    Cached schema information for a customer database table/column.

    One row per column. This is the only data copied from customer databases —
    it contains no business data, only structural metadata.

    The table is rebuilt on every schema sync operation.
    """

    __tablename__ = "schema_metadata"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "schema_name", "table_name", "column_name",
            name="uq_schema_metadata_connection_col",
        ),
        Index("ix_schema_metadata_connection_table", "connection_id", "table_name"),
        Index("ix_schema_metadata_connection_schema", "connection_id", "schema_name"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    table_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary_key: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_foreign_key: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    foreign_table: Mapped[str | None] = mapped_column(String(255), nullable=True)
    foreign_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    character_maximum_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship
    connection: Mapped["DatabaseConnection"] = relationship(
        "DatabaseConnection", back_populates="schema_metadata"
    )

    def __repr__(self) -> str:
        return (
            f"<SchemaMetadata {self.schema_name}.{self.table_name}.{self.column_name}>"
        )
