"""KnowledgeBase, Document, and DocumentChunk repositories."""

from __future__ import annotations

import uuid
from typing import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import Document, KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """Repository for KnowledgeBase management."""

    model = KnowledgeBase

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document management."""

    model = Document

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_kb(
        self, kb_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Sequence[Document]:
        """List documents in a knowledge base."""
        stmt = (
            select(Document)
            .where(Document.knowledge_base_id == kb_id, Document.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for DocumentChunk and vector operations."""

    model = DocumentChunk

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def similarity_search(
        self,
        tenant_id: uuid.UUID,
        kb_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """
        Perform vector similarity search using pgvector's cosine distance operator (<=>).
        Calculates similarity as (1 - distance).
        """
        distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity_expr = 1 - distance_expr

        stmt = (
            select(DocumentChunk, similarity_expr.label("similarity"))
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.tenant_id == tenant_id,
                Document.knowledge_base_id == kb_id,
                Document.status == "ready",
                similarity_expr >= similarity_threshold,
            )
            .order_by(distance_expr.asc())
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return result.all()  # returns list of (DocumentChunk, similarity_score)
