"""PostgreSQL Database Adapter."""

from __future__ import annotations

import time
from typing import Any, Sequence
import asyncpg

from app.adapters.base import BaseDatabaseAdapter, ColumnSchemaInfo, QueryResult
from app.core.exceptions import ConnectionError, SQLTimeoutError, SQLResultTooLargeError


class PostgreSQLAdapter(BaseDatabaseAdapter):
    """PostgreSQL adapter using asyncpg."""

    async def _get_connection(self) -> asyncpg.Connection:
        try:
            return await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                timeout=10,
            )
        except Exception as exc:
            raise ConnectionError(message=f"PostgreSQL connection failed: {exc}") from exc

    async def test_connection(self) -> tuple[bool, float, str]:
        start = time.perf_counter()
        try:
            conn = await self._get_connection()
            await conn.fetchval("SELECT 1")
            await conn.close()
            latency = (time.perf_counter() - start) * 1000
            return True, round(latency, 2), "Successfully connected to PostgreSQL database."
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            return False, round(latency, 2), str(exc)

    async def discover_schema(self) -> Sequence[ColumnSchemaInfo]:
        conn = await self._get_connection()
        query = """
            SELECT 
                c.table_schema as schema_name,
                c.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable = 'YES' as is_nullable,
                c.ordinal_position,
                COALESCE(pk.is_pk, false) as is_primary_key,
                COALESCE(fk.is_fk, false) as is_foreign_key,
                fk.foreign_table,
                fk.foreign_column
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.table_schema, kcu.table_name, kcu.column_name, true as is_pk
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.table_schema = pk.table_schema 
                 AND c.table_name = pk.table_name 
                 AND c.column_name = pk.column_name
            LEFT JOIN (
                SELECT 
                    kcu.table_schema, kcu.table_name, kcu.column_name, true as is_fk,
                    ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name 
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
            ) fk ON c.table_schema = fk.table_schema 
                 AND c.table_name = fk.table_name 
                 AND c.column_name = fk.column_name
            WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY c.table_schema, c.table_name, c.ordinal_position;
        """
        rows = await conn.fetch(query)
        await conn.close()

        return [
            ColumnSchemaInfo(
                schema_name=r["schema_name"],
                table_name=r["table_name"],
                column_name=r["column_name"],
                data_type=r["data_type"],
                is_nullable=r["is_nullable"],
                ordinal_position=r["ordinal_position"],
                is_primary_key=r["is_primary_key"],
                is_foreign_key=r["is_foreign_key"],
                foreign_table=r["foreign_table"],
                foreign_column=r["foreign_column"],
            )
            for r in rows
        ]

    async def execute_read_only(
        self, sql: str, params: dict[str, Any] | None = None, timeout_seconds: int = 30, max_rows: int = 1000
    ) -> QueryResult:
        conn = await self._get_connection()
        start = time.perf_counter()
        tr = conn.transaction(readonly=True)
        await tr.start()

        try:
            stmt = await conn.prepare(sql, timeout=timeout_seconds)
            records = await stmt.fetch(timeout=timeout_seconds)
            await tr.commit()

            if len(records) > max_rows:
                records = records[:max_rows]

            columns = list(records[0].keys()) if records else []
            rows_dict = [dict(r) for r in records]
            latency = (time.perf_counter() - start) * 1000

            return QueryResult(
                columns=columns,
                rows=rows_dict,
                row_count=len(rows_dict),
                execution_time_ms=round(latency, 2),
            )
        except asyncpg.exceptions.QueryCanceledError as exc:
            await tr.rollback()
            raise SQLTimeoutError(message="PostgreSQL query execution timed out.") from exc
        except Exception as exc:
            await tr.rollback()
            raise SQLTimeoutError(message=f"PostgreSQL query execution failed: {exc}") from exc
        finally:
            await conn.close()
