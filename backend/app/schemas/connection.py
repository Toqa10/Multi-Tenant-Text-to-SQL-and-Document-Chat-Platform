"""Database Connection & Security Permissions Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

DbType = Literal["postgresql", "mysql", "sqlserver", "oracle"]


class DatabaseConnectionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    db_type: DbType
    host: str
    port: int
    database_name: str
    username: str
    password: str
    connection_options: dict[str, Any] = Field(default_factory=dict)


class DatabaseConnectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    connection_options: dict[str, Any] | None = None


class DatabaseConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    db_type: str
    host: str
    port: int
    database_name: str
    is_active: bool
    last_tested_at: datetime | None = None
    last_schema_sync_at: datetime | None = None
    created_at: datetime


class ConnectionTestResult(BaseModel):
    success: bool
    latency_ms: float
    message: str


class SchemaColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    foreign_table: str | None = None
    foreign_column: str | None = None


class TablePermissionCreate(BaseModel):
    role_id: uuid.UUID
    schema_name: str
    table_name: str
    can_query: bool = True


class ColumnPermissionCreate(BaseModel):
    role_id: uuid.UUID
    table_name: str
    column_name: str
    is_visible: bool = True
    is_filterable: bool = True


class RowFilterCreate(BaseModel):
    role_id: uuid.UUID
    table_name: str
    filter_expression: str
    description: str | None = None
