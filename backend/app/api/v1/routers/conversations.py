"""Conversations API Router."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.schemas.conversation import ConversationCreate, ConversationRead, MessageRead
from app.services.chat import ChatService

router = APIRouter()


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List user conversations."""
    repo = ConversationRepository(db)
    convs = await repo.list_by_user(tenant_id, current_user.id)
    return [ConversationRead.model_validate(c) for c in convs]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation session."""
    service = ChatService(db)
    return await service.create_conversation(tenant_id, current_user.id, req)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List messages in a conversation."""
    repo = MessageRepository(db)
    msgs = await repo.list_for_conversation(conversation_id)
    return [MessageRead.model_validate(m) for m in msgs]
