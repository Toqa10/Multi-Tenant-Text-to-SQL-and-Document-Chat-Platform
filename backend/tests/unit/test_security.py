"""Unit tests for Security, Encryption, and JWT."""

from __future__ import annotations

import pytest
from app.core.encryption import decrypt, encrypt
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    """Test Argon2id password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_access_token():
    """Test JWT creation and payload decoding."""
    token = create_access_token("user-123", {"tenant_id": "tenant-456"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-456"


def test_fernet_encryption():
    """Test AES Fernet encryption and decryption for credentials."""
    plain = "database_secret_password"
    cipher = encrypt(plain)
    assert cipher != plain
    decrypted = decrypt(cipher)
    assert decrypted == plain
