"""Row-level security filter model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.database_connection import DatabaseConnection


class RowFilter(Base, AuditableMixin):
    """
    Mandatory row-level security filter injected into every SQL query.

    The filter_expression is a SQL WHERE clause fragment (e.g.,
    "tenant_id = 'abc123'" or "region IN ('EU', 'UK')") that is
    automatically appended to generated SQL by the Row Filter Injector node.

    The LLM cannot remove or bypass this filter. It is injected
    server-side after SQL generation and before execution.
    """

    __tablename__ = "row_filters"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "connection_id", "table_name",
            name="uq_row_filters_role_conn_table",
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
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # SQL WHERE clause fragment — must be safe, admin-controlled
    filter_expression: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    role: Mapped["Role"] = relationship("Role")
    connection: Mapped["DatabaseConnection"] = relationship(
        "DatabaseConnection", back_populates="row_filters"
    )

    def __repr__(self) -> str:
        return (
            f"<RowFilter role={self.role_id} "
            f"table={self.table_name} expr={self.filter_expression!r}>"
        )
