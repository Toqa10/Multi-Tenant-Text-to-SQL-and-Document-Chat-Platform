"""Refresh token repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for RefreshToken model operations."""

    model = RefreshToken

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Fetch a non-revoked, non-expired refresh token by its hash.

        Returns None if the token is revoked or expired.
        """
        now = datetime.now(UTC)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Mark a token as revoked."""
        token.revoked = True
        self.session.add(token)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens for a user (logout all sessions)."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def delete_expired(self) -> int:
        """Remove all expired tokens (for periodic cleanup)."""
        from sqlalchemy import delete as sa_delete
        now = datetime.now(UTC)
        stmt = sa_delete(RefreshToken).where(RefreshToken.expires_at <= now)
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
