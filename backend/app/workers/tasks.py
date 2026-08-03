"""Celery background tasks for document processing and schema synchronization."""

from __future__ import annotations

import asyncio
import uuid
import structlog
from app.db.session import get_db_context
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import Document
from app.repositories.knowledge_base import DocumentRepository
from app.services.connection import ConnectionService
from app.services.document import DocumentProcessor
from app.storage.minio import MinIOService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="document.process", bind=True, max_retries=3)
def process_document_task(self, document_id_str: str, tenant_id_str: str) -> dict[str, str]:
    """Background task: Downloads file from MinIO, parses text, chunks, embeds, and stores in pgvector."""
    async def _async_process():
        doc_id = uuid.UUID(document_id_str)
        tenant_id = uuid.UUID(tenant_id_str)

        async with get_db_context() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id_and_tenant(doc_id, tenant_id)
            if not doc:
                return {"status": "error", "message": "Document not found"}

            doc.status = "processing"
            await session.flush()

            try:
                # 1. Download file from MinIO
                minio_service = MinIOService()
                bucket_name = f"tenant-{tenant_id}"
                file_bytes = minio_service.get_file(bucket_name, doc.storage_path)

                # 2. Parse text
                processor = DocumentProcessor()
                text = processor.extract_text(file_bytes, doc.file_type)

                # 3. Chunk text
                chunks = processor.chunk_text(text)

                # 4. Generate embeddings
                embeddings = await processor.generate_embeddings(chunks)

                # 5. Store chunks in database
                for idx, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
                    chunk_row = DocumentChunk(
                        document_id=doc.id,
                        tenant_id=tenant_id,
                        content=chunk_text,
                        chunk_index=idx,
                        embedding=vector,
                        token_count=len(chunk_text.split()),
                    )
                    session.add(chunk_row)

                doc.status = "ready"
                doc.chunk_count = len(chunks)
                await session.flush()

                return {"status": "success", "chunks": str(len(chunks))}

            except Exception as exc:
                doc.status = "failed"
                doc.error_message = str(exc)
                await session.flush()
                raise exc

    return asyncio.run(_async_process())


@celery_app.task(name="schema.sync")
def sync_schema_task(connection_id_str: str, tenant_id_str: str) -> dict[str, str]:
    """Background task: Introspect database schema and update cached metadata."""
    async def _async_sync():
        conn_id = uuid.UUID(connection_id_str)
        tenant_id = uuid.UUID(tenant_id_str)

        async with get_db_context() as session:
            conn_service = ConnectionService(session)
            count = await conn_service.sync_schema(conn_id, tenant_id)
            return {"status": "success", "columns": str(count)}

    return asyncio.run(_async_sync())
