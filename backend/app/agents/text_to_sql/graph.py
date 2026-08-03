"""LangGraph workflow for Text-to-SQL Generation and Execution."""

from __future__ import annotations

import time
import uuid
from typing import Any, TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.text_to_sql.row_filter_injector import RowFilterInjector
from app.agents.text_to_sql.sql_validator import SQLValidator
from app.core.config import get_settings
from app.repositories.permissions import ColumnPermissionRepository, RowFilterRepository, TablePermissionRepository
from app.repositories.schema_metadata import SchemaMetadataRepository
from app.services.connection import ConnectionService

settings = get_settings()


class TextToSQLState(TypedDict):
    question: str
    tenant_id: str
    user_id: str
    role_ids: list[str]
    connection_id: str
    schema_context: str
    generated_sql: str
    validated_sql: str
    query_result: dict[str, Any]
    final_answer: str
    error: str | None
    execution_time_ms: float


class TextToSQLAgent:
    """LangGraph agent for safe Text-to-SQL translation, security enforcement, execution, and answer generation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.schema_repo = SchemaMetadataRepository(session)
        self.table_perm_repo = TablePermissionRepository(session)
        self.col_perm_repo = ColumnPermissionRepository(session)
        self.row_filter_repo = RowFilterRepository(session)
        self.conn_service = ConnectionService(session)
        self.llm = ChatOpenAI(
            api_key=settings.openai.api_key,
            model=settings.openai.model,
            temperature=0.0,
        )

    async def retrieve_schema_node(self, state: TextToSQLState) -> dict[str, Any]:
        """Node 1: Retrieve schema and filter out unauthorized tables/columns."""
        conn_id = uuid.UUID(state["connection_id"])
        role_uuids = [uuid.UUID(r) for r in state["role_ids"]]

        # Get all connection schema metadata
        all_metadata = await self.schema_repo.get_by_connection(conn_id)

        # Get role permissions
        table_perms = await self.table_perm_repo.get_for_roles_and_connection(role_uuids, conn_id)
        forbidden_tables = {tp.table_name.lower() for tp in table_perms if not tp.can_query}

        col_perms = await self.col_perm_repo.get_for_roles_and_connection(role_uuids, conn_id)
        invisible_cols = {(cp.table_name.lower(), cp.column_name.lower()) for cp in col_perms if not cp.is_visible}

        schema_lines = []
        for col in all_metadata:
            t_name = col.table_name.lower()
            c_name = col.column_name.lower()

            if t_name in forbidden_tables:
                continue
            if (t_name, c_name) in invisible_cols:
                continue

            schema_lines.append(f"Table: {col.table_name}, Column: {col.column_name} ({col.data_type})")

        return {"schema_context": "\n".join(schema_lines)}

    async def generate_sql_node(self, state: TextToSQLState) -> dict[str, Any]:
        """Node 2: Generate SQL query using LLM."""
        prompt = f"""
You are an expert SQL generator. Convert the user's question into a clean, read-only SQL SELECT query based ONLY on the provided schema.
Do NOT execute commands, modify data, or use comments.

SCHEMA:
{state['schema_context']}

QUESTION:
{state['question']}

Return ONLY the raw SQL query with no markdown formatting or markdown code blocks.
"""
        response = await self.llm.ainvoke(prompt)
        raw_sql = str(response.content).strip()
        if raw_sql.startswith("```sql"):
            raw_sql = raw_sql[6:]
        if raw_sql.endswith("```"):
            raw_sql = raw_sql[:-3]
        return {"generated_sql": raw_sql.strip()}

    async def validate_and_filter_node(self, state: TextToSQLState) -> dict[str, Any]:
        """Node 3 & 4: Validate SQL and inject mandatory server-side row filters."""
        try:
            # SQLGlot Security Validation
            SQLValidator.validate_sql(state["generated_sql"])

            # Row Filter Injection
            conn_id = uuid.UUID(state["connection_id"])
            role_uuids = [uuid.UUID(r) for r in state["role_ids"]]
            filters = await self.row_filter_repo.get_for_roles_and_connection(role_uuids, conn_id)

            filter_map = {rf.table_name.lower(): rf.filter_expression for rf in filters}
            final_sql = RowFilterInjector.inject_row_filters(state["generated_sql"], filter_map)

            return {"validated_sql": final_sql, "error": None}
        except Exception as exc:
            return {"error": str(exc)}

    async def execute_sql_node(self, state: TextToSQLState) -> dict[str, Any]:
        """Node 5: Execute validated SQL on target database connection."""
        if state.get("error"):
            return {"query_result": {"columns": [], "rows": [], "row_count": 0}}

        conn_id = uuid.UUID(state["connection_id"])
        tenant_id = uuid.UUID(state["tenant_id"])

        adapter = await self.conn_service.get_adapter_for_connection(conn_id, tenant_id)
        result = await adapter.execute_read_only(
            sql=state["validated_sql"],
            timeout_seconds=settings.sql.query_timeout_seconds,
            max_rows=settings.sql.max_result_rows,
        )

        return {
            "query_result": result.model_dump(),
            "execution_time_ms": result.execution_time_ms,
        }

    async def generate_answer_node(self, state: TextToSQLState) -> dict[str, Any]:
        """Node 6: Generate final natural language answer summarizing SQL results."""
        if state.get("error"):
            return {"final_answer": f"Could not execute query due to security policy: {state['error']}"}

        prompt = f"""
You are an AI business analyst. Synthesize a concise, accurate natural language answer to the user's question based on the executed SQL query and its results.

QUESTION:
{state['question']}

SQL QUERY:
{state['validated_sql']}

QUERY RESULT SUMMARY:
Row Count: {state['query_result'].get('row_count', 0)}
Data Sample: {state['query_result'].get('rows', [])[:10]}

Provide a clear, direct answer with proper context.
"""
        response = await self.llm.ainvoke(prompt)
        return {"final_answer": str(response.content).strip()}

    def build_graph(self) -> Any:
        """Assemble StateGraph workflow."""
        workflow = StateGraph(TextToSQLState)

        workflow.add_node("retrieve_schema", self.retrieve_schema_node)
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("validate_and_filter", self.validate_and_filter_node)
        workflow.add_node("execute_sql", self.execute_sql_node)
        workflow.add_node("generate_answer", self.generate_answer_node)

        workflow.set_entry_point("retrieve_schema")
        workflow.add_edge("retrieve_schema", "generate_sql")
        workflow.add_edge("generate_sql", "validate_and_filter")
        workflow.add_edge("validate_and_filter", "execute_sql")
        workflow.add_edge("execute_sql", "generate_answer")
        workflow.add_edge("generate_answer", END)

        return workflow.compile()
