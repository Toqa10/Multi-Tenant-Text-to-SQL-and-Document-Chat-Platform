"""Users Management API Router."""

from __future__ import annotations

import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, require_permission
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserRead])
async def list_users(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user", "manage")),
):
    """List tenant users."""
    repo = UserRepository(db)
    users = await repo.list_by_tenant(tenant_id)
    return [UserRead.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user", "manage")),
):
    """Get tenant user details."""
    repo = UserRepository(db)
    user = await repo.get_by_id_and_tenant(user_id, tenant_id)
    if not user:
        raise NotFoundError(message="User not found.")
    return UserRead.model_validate(user)
