"""Knowledge Bases & Documents API Router."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, require_permission
from app.core.exceptions import NotFoundError, UnsupportedFileTypeError
from app.db.session import get_db
from app.models.user import User
from app.repositories.knowledge_base import DocumentRepository, KnowledgeBaseRepository
from app.schemas.knowledge_base import DocumentRead, KnowledgeBaseCreate, KnowledgeBaseRead
from app.storage.minio import MinIOService
from app.workers.tasks import process_document_task

router = APIRouter()


@router.get("", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge_base", "read")),
):
    """List tenant knowledge bases."""
    repo = KnowledgeBaseRepository(db)
    kbs = await repo.list_by_tenant(tenant_id)
    return [KnowledgeBaseRead.model_validate(k) for k in kbs]


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge_base", "create")),
):
    """Create a new knowledge base."""
    repo = KnowledgeBaseRepository(db)
    kb = await repo.create(
        tenant_id=tenant_id,
        name=req.name,
        description=req.description,
        embedding_model=req.embedding_model,
    )
    return KnowledgeBaseRead.model_validate(kb)


@router.get("/{kb_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    kb_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge_base", "read")),
):
    """List documents in a knowledge base."""
    repo = DocumentRepository(db)
    docs = await repo.list_by_kb(kb_id, tenant_id)
    return [DocumentRead.model_validate(d) for d in docs]


@router.post("/{kb_id}/documents", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("document", "upload")),
):
    """Upload document file and trigger background processing pipeline."""
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_id_and_tenant(kb_id, tenant_id)
    if not kb:
        raise NotFoundError(message="Knowledge base not found.")

    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ("pdf", "docx", "xlsx", "csv", "txt"):
        raise UnsupportedFileTypeError(message=f"File extension '.{ext}' is not supported.")

    file_bytes = await file.read()

    # Upload file to MinIO
    minio_service = MinIOService()
    bucket_name = f"tenant-{tenant_id}"
    storage_path = f"documents/{uuid.uuid4()}/{file.filename}"

    minio_service.upload_file(
        bucket_name=bucket_name,
        object_name=storage_path,
        file_data=file_bytes,
        content_type=file.content_type or "application/octet-stream",
    )

    doc_repo = DocumentRepository(db)
    doc = await doc_repo.create(
        knowledge_base_id=kb_id,
        tenant_id=tenant_id,
        filename=file.filename,
        original_filename=file.filename,
        file_type=ext,
        file_size_bytes=len(file_bytes),
        storage_path=storage_path,
        status="pending",
    )

    # Queue background task for Parsing, Chunking & Vector Embedding
    task = process_document_task.delay(str(doc.id), str(tenant_id))
    doc.celery_task_id = task.id
    await db.flush()

    return DocumentRead.model_validate(doc)
