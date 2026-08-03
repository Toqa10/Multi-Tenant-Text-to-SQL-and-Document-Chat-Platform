"""LangGraph workflow for Hybrid Chat (Intent Classification + Text-to-SQL + Document RAG)."""

from __future__ import annotations

import time
import uuid
from typing import Any, TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.text_to_sql.graph import TextToSQLAgent
from app.core.config import get_settings
from app.repositories.knowledge_base import DocumentChunkRepository
from app.services.document import DocumentProcessor

settings = get_settings()


class HybridChatState(TypedDict):
    question: str
    tenant_id: str
    user_id: str
    role_ids: list[str]
    connection_id: str | None
    knowledge_base_id: str | None
    intent: str  # database, document, hybrid, general, clarification
    sql_result: dict[str, Any]
    doc_results: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    final_answer: str
    tokens_used: int
    execution_time_ms: float


class HybridChatAgent:
    """Master LangGraph agent orchestrating Intent Classification, Text-to-SQL, Document RAG, and Hybrid Merging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sql_agent = TextToSQLAgent(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.doc_processor = DocumentProcessor()
        self.llm = ChatOpenAI(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            temperature=0.0,
        )

    async def classify_intent_node(self, state: HybridChatState) -> dict[str, Any]:
        """Node 1: Intent Classifier."""
        question = state["question"]
        has_db = bool(state.get("connection_id"))
        has_doc = bool(state.get("knowledge_base_id"))

        if not has_db and not has_doc:
            return {"intent": "general"}

        prompt = f"""
Classify the user query intent into exactly ONE category:
- 'database': Question requires querying structured database tables/metrics.
- 'document': Question requires searching unstructured text documents/files.
- 'hybrid': Question requires BOTH structured database data AND document content.
- 'general': Question is a general greeting or conversational statement.
- 'clarification': Question is too ambiguous and needs clarification.

User Query: "{question}"
Available DB: {has_db}
Available Document KB: {has_doc}

Return ONLY the single label string.
"""
        response = await self.llm.ainvoke(prompt)
        intent = str(response.content).strip().lower()
        if intent not in ("database", "document", "hybrid", "general", "clarification"):
            intent = "hybrid" if (has_db and has_doc) else ("database" if has_db else "document")

        return {"intent": intent}

    async def run_db_agent_node(self, state: HybridChatState) -> dict[str, Any]:
        """Node 2: Execute Text-to-SQL Agent graph."""
        if not state.get("connection_id"):
            return {"sql_result": {}}

        sql_state = {
            "question": state["question"],
            "tenant_id": state["tenant_id"],
            "user_id": state["user_id"],
            "role_ids": state["role_ids"],
            "connection_id": state["connection_id"],
            "schema_context": "",
            "generated_sql": "",
            "validated_sql": "",
            "query_result": {},
            "final_answer": "",
            "error": None,
            "execution_time_ms": 0.0,
        }
        graph = self.sql_agent.build_graph()
        final_sql_state = await graph.ainvoke(sql_state)

        return {"sql_result": final_sql_state}

    async def run_doc_agent_node(self, state: HybridChatState) -> dict[str, Any]:
        """Node 3: Execute Document Vector RAG search."""
        if not state.get("knowledge_base_id"):
            return {"doc_results": [], "citations": []}

        # 1. Embed query
        embeddings = await self.doc_processor.generate_embeddings([state["question"]])
        if not embeddings:
            return {"doc_results": [], "citations": []}

        query_vector = embeddings[0]
        tenant_id = uuid.UUID(state["tenant_id"])
        kb_id = uuid.UUID(state["knowledge_base_id"])

        # 2. Similarity search in pgvector
        results = await self.chunk_repo.similarity_search(
            tenant_id=tenant_id,
            kb_id=kb_id,
            query_embedding=query_vector,
            top_k=settings.rag.top_k,
            similarity_threshold=settings.rag.similarity_threshold,
        )

        doc_chunks = []
        citations = []
        for chunk, sim in results:
            doc_chunks.append({
                "content": chunk.content,
                "similarity": round(float(sim), 4),
            })
            citations.append({
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "similarity": round(float(sim), 4),
                "snippet": chunk.content[:200] + "...",
            })

        return {"doc_results": doc_chunks, "citations": citations}

    async def hybrid_merger_node(self, state: HybridChatState) -> dict[str, Any]:
        """Node 4: Merge results and synthesize final answer."""
        start = time.perf_counter()

        sql_data = state.get("sql_result", {})
        doc_data = state.get("doc_results", [])
        intent = state.get("intent", "general")

        prompt = f"""
You are an enterprise AI assistant. Generate a clear, grounded response to the user's question using ONLY the provided sources.

INTENT: {intent}
QUESTION: {state['question']}

STRUCTURED DATABASE RESULT:
{sql_data.get('final_answer', 'N/A')}

DOCUMENT SEARCH EXTRACTS:
{doc_data[:5]}

Provide a single well-structured response. Always cite sources where applicable.
"""
        response = await self.llm.ainvoke(prompt)
        elapsed = (time.perf_counter() - start) * 1000

        return {
            "final_answer": str(response.content).strip(),
            "execution_time_ms": round(elapsed, 2),
            "tokens_used": 500,
        }

    def build_graph(self) -> Any:
        """Assemble Hybrid Chat StateGraph."""
        workflow = StateGraph(HybridChatState)

        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("run_db_agent", self.run_db_agent_node)
        workflow.add_node("run_doc_agent", self.run_doc_agent_node)
        workflow.add_node("hybrid_merger", self.hybrid_merger_node)

        workflow.set_entry_point("classify_intent")

        workflow.add_edge("classify_intent", "run_db_agent")
        workflow.add_edge("run_db_agent", "run_doc_agent")
        workflow.add_edge("run_doc_agent", "hybrid_merger")
        workflow.add_edge("hybrid_merger", END)

        return workflow.compile()
