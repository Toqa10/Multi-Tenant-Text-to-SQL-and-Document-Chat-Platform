"""Roles & Permissions API Router."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, require_permission
from app.db.session import get_db
from app.models.user import User
from app.repositories.role import PermissionRepository, RoleRepository
from app.schemas.role import PermissionRead, RoleCreate, RoleRead

router = APIRouter()


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role", "manage")),
):
    """List all global permissions."""
    repo = PermissionRepository(db)
    perms = await repo.list_all()
    return [PermissionRead.model_validate(p) for p in perms]


@router.get("", response_model=list[RoleRead])
async def list_roles(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role", "manage")),
):
    """List tenant roles."""
    repo = RoleRepository(db)
    roles = await repo.list_by_tenant(tenant_id)
    return [RoleRead.model_validate(r) for r in roles]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    req: RoleCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role", "manage")),
):
    """Create a custom tenant role."""
    repo = RoleRepository(db)
    perm_repo = PermissionRepository(db)

    role = await repo.create(
        tenant_id=tenant_id,
        name=req.name,
        description=req.description,
    )

    if req.permission_ids:
        for p_id in req.permission_ids:
            p = await perm_repo.get_by_id(p_id)
            if p:
                role.permissions.append(p)
        await db.flush()

    return RoleRead.model_validate(role)
