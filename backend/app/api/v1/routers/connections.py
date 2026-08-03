"""Database Connections API Router."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, require_permission
from app.db.session import get_db
from app.models.user import User
from app.repositories.database_connection import DatabaseConnectionRepository
from app.repositories.permissions import ColumnPermissionRepository, RowFilterRepository, TablePermissionRepository
from app.schemas.connection import (
    ColumnPermissionCreate,
    ConnectionTestResult,
    DatabaseConnectionCreate,
    DatabaseConnectionRead,
    RowFilterCreate,
    SchemaColumnRead,
    TablePermissionCreate,
)
from app.services.connection import ConnectionService

router = APIRouter()


@router.get("", response_model=list[DatabaseConnectionRead])
async def list_connections(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("connection", "read")),
):
    """List tenant database connections."""
    repo = DatabaseConnectionRepository(db)
    conns = await repo.list_by_tenant(tenant_id)
    return [DatabaseConnectionRead.model_validate(c) for c in conns]


@router.post("", response_model=DatabaseConnectionRead, status_code=status.HTTP_201_CREATED)
async def create_connection(
    req: DatabaseConnectionCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("connection", "create")),
):
    """Create a new external runtime database connection."""
    service = ConnectionService(db)
    conn = await service.create_connection(tenant_id, req)
    return DatabaseConnectionRead.model_validate(conn)


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("connection", "test")),
):
    """Test external database connection."""
    service = ConnectionService(db)
    success, latency, msg = await service.test_connection(connection_id, tenant_id)
    return ConnectionTestResult(success=success, latency_ms=latency, message=msg)


@router.post("/{connection_id}/sync-schema")
async def sync_schema(
    connection_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("connection", "sync")),
):
    """Discover and cache schema metadata for a database connection."""
    service = ConnectionService(db)
    count = await service.sync_schema(connection_id, tenant_id)
    return {"message": "Schema synchronization complete.", "discovered_columns": count}


@router.get("/{connection_id}/schema", response_model=list[SchemaColumnRead])
async def get_schema(
    connection_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("connection", "read")),
):
    """Get discovered schema metadata."""
    service = ConnectionService(db)
    metadata = await service.get_schema_metadata(connection_id, tenant_id)
    return [SchemaColumnRead.model_validate(m) for m in metadata]


@router.post("/{connection_id}/permissions/tables", status_code=status.HTTP_201_CREATED)
async def create_table_permission(
    connection_id: uuid.UUID,
    req: TablePermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("permission", "manage")),
):
    """Set table-level query permission for a role."""
    repo = TablePermissionRepository(db)
    perm = await repo.create(
        role_id=req.role_id,
        connection_id=connection_id,
        schema_name=req.schema_name,
        table_name=req.table_name,
        can_query=req.can_query,
    )
    return {"message": "Table permission created", "id": str(perm.id)}


@router.post("/{connection_id}/permissions/columns", status_code=status.HTTP_201_CREATED)
async def create_column_permission(
    connection_id: uuid.UUID,
    req: ColumnPermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("permission", "manage")),
):
    """Set column-level visibility and filterability permission for a role."""
    repo = ColumnPermissionRepository(db)
    perm = await repo.create(
        role_id=req.role_id,
        connection_id=connection_id,
        table_name=req.table_name,
        column_name=req.column_name,
        is_visible=req.is_visible,
        is_filterable=req.is_filterable,
    )
    return {"message": "Column permission created", "id": str(perm.id)}


@router.post("/{connection_id}/permissions/rows", status_code=status.HTTP_201_CREATED)
async def create_row_filter(
    connection_id: uuid.UUID,
    req: RowFilterCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("permission", "manage")),
):
    """Set mandatory row-level security WHERE clause filter for a role."""
    repo = RowFilterRepository(db)
    rf = await repo.create(
        role_id=req.role_id,
        connection_id=connection_id,
        table_name=req.table_name,
        filter_expression=req.filter_expression,
        description=req.description,
    )
    return {"message": "Row filter created", "id": str(rf.id)}
