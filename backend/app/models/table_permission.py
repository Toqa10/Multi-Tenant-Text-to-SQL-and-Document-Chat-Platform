"""Table, column, and row-level permission models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.database_connection import DatabaseConnection


class TablePermission(Base, AuditableMixin):
    """
    Controls which roles may query a specific table.

    If no TablePermission row exists for (role, connection, table),
    access is denied by default (deny-by-default policy).
    """

    __tablename__ = "table_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "connection_id", "schema_name", "table_name",
            name="uq_table_permissions_role_conn_table",
        ),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_name: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    can_query: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role")
    connection: Mapped["DatabaseConnection"] = relationship(
        "DatabaseConnection", back_populates="table_permissions"
    )

    def __repr__(self) -> str:
        return (
            f"<TablePermission role={self.role_id} "
            f"table={self.schema_name}.{self.table_name} can_query={self.can_query}>"
        )
