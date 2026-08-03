"""
Security utilities: password hashing and JWT token management.

Design decisions:
- Argon2id is used for password hashing (recommended over bcrypt for new systems).
- Access tokens are short-lived (15 min by default).
- Refresh tokens are long-lived (7 days) and stored as hashed values in the DB
  so a compromised database cannot be used to forge sessions.
- Token rotation: each refresh produces a new refresh token and invalidates the old one.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import TokenExpiredError, TokenInvalidError

settings = get_settings()

# ─────────────────────────────────────────────────────────────
# Password Hashing
# ─────────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MiB
    argon2__time_cost=3,
    argon2__parallelism=4,
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using Argon2id.

    Args:
        plain_password: The raw password from the user.

    Returns:
        Argon2id hash string safe to store in the database.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against an Argon2id hash.

    Args:
        plain_password: The raw password to verify.
        hashed_password: The stored Argon2id hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a stored hash needs to be upgraded.

    Returns True when the hash parameters are outdated and the
    password should be rehashed on next successful login.
    """
    return _pwd_context.needs_update(hashed_password)


# ─────────────────────────────────────────────────────────────
# JWT Tokens
# ─────────────────────────────────────────────────────────────

_JWT_SETTINGS = settings.jwt


def create_access_token(
    subject: str,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: The token subject (typically user_id as a string).
        additional_claims: Optional extra claims (tenant_id, roles, etc.).

    Returns:
        Signed JWT string.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=_JWT_SETTINGS.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, _JWT_SETTINGS.secret_key, algorithm=_JWT_SETTINGS.algorithm)


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    """
    Create a long-lived opaque refresh token.

    The token itself is a cryptographically secure random hex string.
    Only its SHA-256 hash is stored in the database.

    Args:
        subject: The token subject (user_id).

    Returns:
        Tuple of (plain_token, expiry_datetime).
        Store only the hash of plain_token; return plain_token to the client.
    """
    plain_token = secrets.token_hex(64)  # 128 hex chars = 512 bits of entropy
    expires_at = datetime.now(UTC) + timedelta(days=_JWT_SETTINGS.refresh_token_expire_days)
    return plain_token, expires_at


def hash_refresh_token(plain_token: str) -> str:
    """
    Hash a plain refresh token using SHA-256.

    Args:
        plain_token: The plain refresh token string.

    Returns:
        Hex-encoded SHA-256 digest safe to store in the database.
    """
    return hashlib.sha256(plain_token.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary.

    Raises:
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is malformed or signature is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            _JWT_SETTINGS.secret_key,
            algorithms=[_JWT_SETTINGS.algorithm],
        )
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError() from exc
        raise TokenInvalidError() from exc

    if payload.get("type") != "access":
        raise TokenInvalidError(message="Not an access token.")

    return payload


def extract_user_id(token: str) -> str:
    """
    Extract the user_id (subject) from a validated access token.

    Args:
        token: Validated JWT access token string.

    Returns:
        The user_id string from the 'sub' claim.

    Raises:
        TokenInvalidError: If the 'sub' claim is missing.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidError(message="Token is missing 'sub' claim.")
    return str(user_id)
