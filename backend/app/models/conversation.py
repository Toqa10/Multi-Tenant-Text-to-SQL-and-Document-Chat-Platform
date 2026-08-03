"""Conversation and Message models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.database_connection import DatabaseConnection
    from app.models.knowledge_base import KnowledgeBase


class Conversation(Base, AuditableMixin):
    """
    A named conversation session.

    mode determines which agents are activated:
    - database: Text-to-SQL only
    - document: RAG only
    - hybrid: Both SQL + RAG merged
    - general: General chat (no retrieval)
    """

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('database', 'document', 'hybrid', 'general')",
            name="ck_conversations_mode",
        ),
        Index("ix_conversations_tenant_user", "tenant_id", "user_id"),
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
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New Conversation")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="hybrid")
    # Optional connection for database-mode conversations
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Optional knowledge base for document-mode conversations
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    connection: Mapped["DatabaseConnection | None"] = relationship(
        "DatabaseConnection", back_populates="conversations"
    )
    knowledge_base: Mapped["KnowledgeBase | None"] = relationship(
        "KnowledgeBase", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} mode={self.mode!r} user={self.user_id}>"


class Message(Base, AuditableMixin):
    """
    A single turn in a conversation.

    role is either 'user' or 'assistant'.
    sql_query and sql_result are populated for database-mode responses.
    citations is a JSON array of document chunk references for RAG responses.
    """

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Populated for SQL-based answers
    sql_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Populated for RAG-based answers: [{doc_name, chunk_index, page, snippet}]
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Token usage for cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationship
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} role={self.role!r} "
            f"conv={self.conversation_id} tokens={self.tokens_used}>"
        )
