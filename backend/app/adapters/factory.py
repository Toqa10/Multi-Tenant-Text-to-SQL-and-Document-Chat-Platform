"""Database Adapter Factory."""

from __future__ import annotations

from typing import Any
from app.adapters.base import BaseDatabaseAdapter
from app.adapters.mysql import MySQLAdapter, OracleAdapter, SQLServerAdapter
from app.adapters.postgres import PostgreSQLAdapter
from app.core.exceptions import UnsupportedDatabaseTypeError


class DatabaseAdapterFactory:
    """Factory creating appropriate database adapter instance based on db_type."""

    @staticmethod
    def get_adapter(
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        options: dict[str, Any] | None = None,
    ) -> BaseDatabaseAdapter:
        db_type_lower = db_type.lower()
        if db_type_lower == "postgresql":
            return PostgreSQLAdapter(host, port, database, username, password, options)
        elif db_type_lower == "mysql":
            return MySQLAdapter(host, port, database, username, password, options)
        elif db_type_lower == "sqlserver":
            return SQLServerAdapter(host, port, database, username, password, options)
        elif db_type_lower == "oracle":
            return OracleAdapter(host, port, database, username, password, options)
        else:
            raise UnsupportedDatabaseTypeError(
                message=f"Database adapter for type '{db_type}' is not supported."
            )
