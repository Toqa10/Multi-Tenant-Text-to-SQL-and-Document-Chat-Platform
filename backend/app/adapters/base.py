"""Base Database Adapter Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence
from pydantic import BaseModel


class ColumnSchemaInfo(BaseModel):
    schema_name: str
    table_name: str
    table_comment: str | None = None
    column_name: str
    column_comment: str | None = None
    data_type: str
    is_nullable: bool
    ordinal_position: int
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: str | None = None
    foreign_column: str | None = None


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float


class BaseDatabaseAdapter(ABC):
    """Abstract base class for all external runtime database connection adapters."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.options = options or {}

    @abstractmethod
    async def test_connection(self) -> tuple[bool, float, str]:
        """Test database connection. Returns (success, latency_ms, message)."""
        pass

    @abstractmethod
    async def discover_schema(self) -> Sequence[ColumnSchemaInfo]:
        """Introspect database schema and return metadata."""
        pass

    @abstractmethod
    async def execute_read_only(
        self, sql: str, params: dict[str, Any] | None = None, timeout_seconds: int = 30, max_rows: int = 1000
    ) -> QueryResult:
        """Execute validated read-only SQL query with timeout and row limit."""
        pass
