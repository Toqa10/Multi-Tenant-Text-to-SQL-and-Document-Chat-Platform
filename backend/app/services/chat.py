"""Chat Service handling full conversation turns and audit logging."""

from __future__ import annotations

import time
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hybrid.graph import HybridChatAgent
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository, QueryLogRepository
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.schemas.conversation import ChatRequest, ChatResponse, ConversationCreate, ConversationRead


class ChatService:
    """Orchestrates conversations, invokes hybrid agents, records message history and query audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.query_log_repo = QueryLogRepository(session)
        self.audit_log_repo = AuditLogRepository(session)
        self.agent = HybridChatAgent(session)

    async def create_conversation(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, req: ConversationCreate
    ) -> ConversationRead:
        """Create a new conversation session."""
        conv = await self.conv_repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            title=req.title,
            mode=req.mode,
            connection_id=req.connection_id,
            knowledge_base_id=req.knowledge_base_id,
        )
        return ConversationRead.model_validate(conv)

    async def process_chat_message(
        self, user: User, req: ChatRequest
    ) -> ChatResponse:
        """Process user message, execute agent graph, persist turn and return response."""
        start_time = time.perf_counter()

        conv = await self.conv_repo.get_by_id_and_tenant(req.conversation_id, user.tenant_id)
        if not conv:
            raise NotFoundError(message="Conversation not found.")

        # Save user message
        await self.msg_repo.create(
            conversation_id=conv.id,
            role="user",
            content=req.message,
        )

        role_ids = [str(r.id) for r in user.roles]

        # State for hybrid agent
        state = {
            "question": req.message,
            "tenant_id": str(user.tenant_id),
            "user_id": str(user.id),
            "role_ids": role_ids,
            "connection_id": str(conv.connection_id) if conv.connection_id else None,
            "knowledge_base_id": str(conv.knowledge_base_id) if conv.knowledge_base_id else None,
            "intent": "general",
            "sql_result": {},
            "doc_results": [],
            "citations": [],
            "final_answer": "",
            "tokens_used": 0,
            "execution_time_ms": 0.0,
        }

        graph = self.agent.build_graph()
        final_state = await graph.ainvoke(state)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        sql_state = final_state.get("sql_result", {})
        gen_sql = sql_state.get("validated_sql")
        sql_res = sql_state.get("query_result")

        # Save assistant message
        asst_msg = await self.msg_repo.create(
            conversation_id=conv.id,
            role="assistant",
            content=final_state.get("final_answer", ""),
            sql_query=gen_sql,
            sql_result=sql_res,
            citations=final_state.get("citations", []),
            tokens_used=final_state.get("tokens_used", 0),
            intent=final_state.get("intent"),
            latency_ms=int(elapsed_ms),
        )

        # Audit QueryLog if SQL was executed
        if gen_sql and conv.connection_id:
            await self.query_log_repo.create(
                tenant_id=user.tenant_id,
                user_id=user.id,
                connection_id=conv.connection_id,
                conversation_id=conv.id,
                raw_question=req.message,
                generated_sql=gen_sql,
                execution_time_ms=int(sql_state.get("execution_time_ms", 0)),
                row_count=sql_res.get("row_count", 0) if sql_res else 0,
                status="failed" if sql_state.get("error") else "success",
                error_message=sql_state.get("error"),
            )

        return ChatResponse(
            conversation_id=conv.id,
            message_id=asst_msg.id,
            role="assistant",
            content=asst_msg.content,
            intent=final_state.get("intent", "general"),
            sql_query=gen_sql,
            sql_result=sql_res,
            citations=final_state.get("citations", []),
            tokens_used=asst_msg.tokens_used,
            latency_ms=int(elapsed_ms),
        )
