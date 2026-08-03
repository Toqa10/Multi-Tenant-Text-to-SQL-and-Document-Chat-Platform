"""FastAPI dependencies for Authentication, Tenant Isolation, and RBAC."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError, TenantIsolationError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate access token and return current authenticated user.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    tenant_id_str = payload.get("tenant_id")

    if not user_id_str or not tenant_id_str:
        raise AuthenticationError(message="Invalid token claims.")

    user_id = uuid.UUID(user_id_str)
    tenant_id = uuid.UUID(tenant_id_str)

    user_repo = UserRepository(db)
    user = await user_repo.get_active_by_id_and_tenant(user_id, tenant_id)

    if not user:
        raise AuthenticationError(message="User not found or inactive.")

    return user


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    """Extract and enforce tenant_id from current authenticated user."""
    if not current_user.tenant_id:
        raise TenantIsolationError()
    return current_user.tenant_id


def require_permission(resource: str, action: str) -> Callable[..., User]:
    """
    Dependency factory enforcing RBAC permission requirement.
    Checks if user is superuser OR user has role with (resource, action) permission.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        # Check assigned roles and their permissions
        has_perm = False
        for role in current_user.roles:
            for perm in role.permissions:
                if perm.resource == resource and perm.action == action:
                    has_perm = True
                    break
            if has_perm:
                break

        if not has_perm:
            raise PermissionDeniedError(
                message=f"Required permission '{resource}:{action}' is missing."
            )

        return current_user

    return permission_checker
