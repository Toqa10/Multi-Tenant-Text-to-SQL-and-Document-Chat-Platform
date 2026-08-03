"""Conversation and Chat Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

ChatMode = Literal["database", "document", "hybrid", "general"]


class ConversationCreate(BaseModel):
    title: str = Field(default="New Conversation", max_length=500)
    mode: ChatMode = "hybrid"
    connection_id: uuid.UUID | None = None
    knowledge_base_id: uuid.UUID | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    mode: str
    connection_id: uuid.UUID | None = None
    knowledge_base_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sql_query: str | None = None
    sql_result: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    tokens_used: int
    intent: str | None = None
    latency_ms: int
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str = "assistant"
    content: str
    intent: str
    sql_query: str | None = None
    sql_result: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    tokens_used: int
    latency_ms: int
