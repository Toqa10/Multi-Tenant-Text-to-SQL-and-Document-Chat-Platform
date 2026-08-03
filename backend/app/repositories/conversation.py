"""Conversation and Message repositories."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation operations."""

    model = Conversation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_messages(
        self, conversation_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        """Fetch conversation with ordered messages eagerly loaded."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
            )
            .options(selectinload(Conversation.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50
    ) -> Sequence[Conversation]:
        """List user's conversations ordered by update time."""
        stmt = (
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id, Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class MessageRepository(BaseRepository[Message]):
    """Repository for Message operations."""

    model = Message

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_conversation(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> Sequence[Message]:
        """List messages in chronological order."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
