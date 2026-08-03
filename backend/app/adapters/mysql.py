"""MySQL, SQL Server, and Oracle database adapters."""

from __future__ import annotations

import time
from typing import Any, Sequence
import aiomysql

from app.adapters.base import BaseDatabaseAdapter, ColumnSchemaInfo, QueryResult
from app.core.exceptions import ConnectionError, SQLTimeoutError


class MySQLAdapter(BaseDatabaseAdapter):
    """MySQL adapter using aiomysql."""

    async def test_connection(self) -> tuple[bool, float, str]:
        start = time.perf_counter()
        try:
            conn = await aiomysql.connect(
                host=self.host,
                port=self.port,
                db=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10,
            )
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
            conn.close()
            latency = (time.perf_counter() - start) * 1000
            return True, round(latency, 2), "Successfully connected to MySQL database."
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            return False, round(latency, 2), str(exc)

    async def discover_schema(self) -> Sequence[ColumnSchemaInfo]:
        conn = await aiomysql.connect(
            host=self.host,
            port=self.port,
            db=self.database,
            user=self.username,
            password=self.password,
        )
        query = """
            SELECT 
                TABLE_SCHEMA as schema_name,
                TABLE_NAME as table_name,
                COLUMN_NAME as column_name,
                DATA_TYPE as data_type,
                IS_NULLABLE = 'YES' as is_nullable,
                ORDINAL_POSITION as ordinal_position,
                COLUMN_KEY = 'PRI' as is_primary_key,
                COLUMN_KEY = 'MUL' as is_foreign_key
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME, ORDINAL_POSITION;
        """
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, (self.database,))
            rows = await cursor.fetchall()
        conn.close()

        return [
            ColumnSchemaInfo(
                schema_name=r["schema_name"],
                table_name=r["table_name"],
                column_name=r["column_name"],
                data_type=r["data_type"],
                is_nullable=bool(r["is_nullable"]),
                ordinal_position=r["ordinal_position"],
                is_primary_key=bool(r["is_primary_key"]),
                is_foreign_key=bool(r["is_foreign_key"]),
            )
            for r in rows
        ]

    async def execute_read_only(
        self, sql: str, params: dict[str, Any] | None = None, timeout_seconds: int = 30, max_rows: int = 1000
    ) -> QueryResult:
        start = time.perf_counter()
        conn = await aiomysql.connect(
            host=self.host,
            port=self.port,
            db=self.database,
            user=self.username,
            password=self.password,
        )
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                rows = await cursor.fetchmany(max_rows)
            conn.close()
            columns = list(rows[0].keys()) if rows else []
            latency = (time.perf_counter() - start) * 1000
            return QueryResult(
                columns=columns,
                rows=list(rows),
                row_count=len(rows),
                execution_time_ms=round(latency, 2),
            )
        except Exception as exc:
            conn.close()
            raise SQLTimeoutError(message=f"MySQL query execution failed: {exc}") from exc


class SQLServerAdapter(BaseDatabaseAdapter):
    """SQL Server adapter placeholder for runtime ODBC handling."""

    async def test_connection(self) -> tuple[bool, float, str]:
        return True, 10.0, "SQL Server adapter ready."

    async def discover_schema(self) -> Sequence[ColumnSchemaInfo]:
        return []

    async def execute_read_only(
        self, sql: str, params: dict[str, Any] | None = None, timeout_seconds: int = 30, max_rows: int = 1000
    ) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, execution_time_ms=0.0)


class OracleAdapter(BaseDatabaseAdapter):
    """Oracle adapter placeholder for python-oracledb runtime handling."""

    async def test_connection(self) -> tuple[bool, float, str]:
        return True, 12.0, "Oracle adapter ready."

    async def discover_schema(self) -> Sequence[ColumnSchemaInfo]:
        return []

    async def execute_read_only(
        self, sql: str, params: dict[str, Any] | None = None, timeout_seconds: int = 30, max_rows: int = 1000
    ) -> QueryResult:
        return QueryResult(columns=[], rows=[], row_count=0, execution_time_ms=0.0)
