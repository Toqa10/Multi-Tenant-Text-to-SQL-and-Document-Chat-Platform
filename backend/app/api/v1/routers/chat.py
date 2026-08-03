"""Chat API Router (JSON & SSE Streaming)."""

from __future__ import annotations

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send user message to AI Agent (Hybrid / Text-to-SQL / RAG) and receive answer."""
    service = ChatService(db)
    return await service.process_chat_message(current_user, req)


@router.post("/message/stream")
async def send_chat_message_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) streaming endpoint for real-time chat responses."""
    service = ChatService(db)

    async def event_generator():
        yield f"data: {json.dumps({'event': 'start', 'message': 'Processing question...'})}\n\n"
        response = await service.process_chat_message(current_user, req)
        yield f"data: {json.dumps({'event': 'result', 'data': response.model_dump(mode='json')})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
