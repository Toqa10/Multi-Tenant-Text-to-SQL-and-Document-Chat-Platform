"""Query log model — SQL execution audit trail."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.database_connection import DatabaseConnection


class QueryLog(Base, AuditableMixin):
    """
    Detailed log of every SQL query generated and executed.

    This provides a full audit trail: the original natural language question,
    the generated SQL, execution timing, row count, and any error.
    Used for security review, debugging, and usage analytics.
    """

    __tablename__ = "query_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed', 'rejected', 'timeout')",
            name="ck_query_logs_status",
        ),
        Index("ix_query_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_query_logs_user_created", "user_id", "created_at"),
        Index("ix_query_logs_connection", "connection_id"),
        Index("ix_query_logs_status", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Rejection reason if SQL was blocked by security rules
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="query_logs")
    connection: Mapped["DatabaseConnection | None"] = relationship(
        "DatabaseConnection", back_populates="query_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<QueryLog id={self.id} status={self.status!r} "
            f"exec_ms={self.execution_time_ms}>"
        )
