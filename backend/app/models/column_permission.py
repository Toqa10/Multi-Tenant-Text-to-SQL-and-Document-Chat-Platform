"""Column-level permission model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.database_connection import DatabaseConnection


class ColumnPermission(Base, AuditableMixin):
    """
    Controls visibility and filterability of specific columns per role.

    - is_visible=False: The column is excluded from SELECT results.
    - is_filterable=False: The column may not be used in WHERE clauses.

    Both flags default to True (columns are visible and filterable unless restricted).
    """

    __tablename__ = "column_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "connection_id", "table_name", "column_name",
            name="uq_column_permissions_role_conn_col",
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
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_filterable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role")
    connection: Mapped["DatabaseConnection"] = relationship(
        "DatabaseConnection", back_populates="column_permissions"
    )

    def __repr__(self) -> str:
        return (
            f"<ColumnPermission role={self.role_id} "
            f"col={self.table_name}.{self.column_name} "
            f"visible={self.is_visible} filterable={self.is_filterable}>"
        )
