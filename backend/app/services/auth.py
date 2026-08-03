"""Authentication Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, RefreshTokenRevokedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.role import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, Token


class AuthService:
    """Service handling User registration, login, JWT issuance, and session management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.tenant_repo = TenantRepository(session)
        self.role_repo = RoleRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)

    async def register(self, req: RegisterRequest) -> tuple[User, Token]:
        """Register a new tenant and admin user."""
        existing_tenant = await self.tenant_repo.get_by_slug(req.tenant_slug)
        if existing_tenant:
            raise ConflictError(message=f"Tenant slug '{req.tenant_slug}' is already registered.")

        # Create Tenant
        tenant = await self.tenant_repo.create(
            name=req.tenant_name,
            slug=req.tenant_slug.lower(),
        )

        # Create Admin Role for Tenant
        admin_role = await self.role_repo.create(
            tenant_id=tenant.id,
            name="Admin",
            description="Tenant administrator with full privileges",
        )

        # Create User
        user = await self.user_repo.create(
            tenant_id=tenant.id,
            email=req.email.lower(),
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            is_active=True,
            is_superuser=False,
        )

        # Assign Admin role to user
        user.roles.append(admin_role)
        await self.session.flush()

        tokens = await self._generate_tokens(user)
        return user, tokens

    async def login(self, req: LoginRequest) -> Token:
        """Authenticate user by tenant slug, email, and password."""
        tenant = await self.tenant_repo.get_by_slug(req.tenant_slug)
        if not tenant or not tenant.is_active:
            raise AuthenticationError(message="Invalid tenant or credentials.")

        user = await self.user_repo.get_by_email_and_tenant(req.email, tenant.id)
        if not user or not user.is_active:
            raise AuthenticationError(message="Invalid tenant or credentials.")

        if not verify_password(req.password, user.hashed_password):
            raise AuthenticationError(message="Invalid tenant or credentials.")

        return await self._generate_tokens(user)

    async def refresh_tokens(self, plain_refresh_token: str) -> Token:
        """Rotate refresh token and issue new access token."""
        token_hash = hash_refresh_token(plain_refresh_token)
        refresh_record = await self.refresh_repo.get_valid_by_hash(token_hash)

        if not refresh_record:
            raise RefreshTokenRevokedError()

        user = await self.user_repo.get_by_id_with_roles(refresh_record.user_id)
        if not user or not user.is_active:
            raise AuthenticationError(message="User is inactive or deleted.")

        # Revoke old refresh token (Token rotation)
        await self.refresh_repo.revoke(refresh_record)

        return await self._generate_tokens(user)

    async def logout(self, plain_refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        token_hash = hash_refresh_token(plain_refresh_token)
        refresh_record = await self.refresh_repo.get_valid_by_hash(token_hash)
        if refresh_record:
            await self.refresh_repo.revoke(refresh_record)

    async def _generate_tokens(self, user: User) -> Token:
        """Helper to create access and refresh token pair."""
        roles_list = [r.name for r in user.roles]
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "tenant_id": str(user.tenant_id),
                "roles": roles_list,
                "is_superuser": user.is_superuser,
            },
        )

        plain_refresh_token, expires_at = create_refresh_token(str(user.id))
        token_hash = hash_refresh_token(plain_refresh_token)

        await self.refresh_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )

        return Token(
            access_token=access_token,
            refresh_token=plain_refresh_token,
            expires_in=15 * 60,  # 15 mins
        )
