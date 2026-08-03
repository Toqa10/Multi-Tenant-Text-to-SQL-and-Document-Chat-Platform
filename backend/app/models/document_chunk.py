"""Document chunk model with pgvector embedding."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

if TYPE_CHECKING:
    from app.models.knowledge_base import Document


class DocumentChunk(Base, AuditableMixin):
    """
    A single chunk of a processed document with its embedding vector.

    The embedding column uses pgvector's VECTOR type.
    An HNSW index is created in the Alembic migration for fast ANN search.

    Embedding dimension is 1536 for text-embedding-3-small.
    This constant must match the configured embedding model.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        # GIN index on metadata for fast JSONB queries
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_tenant_id", "tenant_id"),
    )

    # Embedding vector dimension — change if switching embedding models
    EMBEDDING_DIM: int = 1536

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Vector embedding stored by pgvector
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    # Citation metadata: page_number, section, headings, etc.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk doc={self.document_id} idx={self.chunk_index} "
            f"tokens={self.token_count}>"
        )
