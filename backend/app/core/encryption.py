"""
Symmetric encryption for sensitive data (e.g., database connection credentials).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
The encryption key is loaded from the ENCRYPTION_KEY environment variable
and must never be stored in the database or version control.

Design decisions:
- Fernet guarantees confidentiality and integrity (authenticated encryption).
- Each encrypt() call produces a unique ciphertext (Fernet includes a random IV).
- The key must be a URL-safe base64-encoded 32-byte value generated with
  Fernet.generate_key().
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import PlatformException

_settings = get_settings()


class EncryptionError(PlatformException):
    """Raised when encryption or decryption fails."""

    status_code = 500
    error_code = "ENCRYPTION_ERROR"
    message = "An encryption/decryption error occurred."


def _get_fernet() -> Fernet:
    """
    Instantiate a Fernet cipher using the application encryption key.

    Raises:
        EncryptionError: If the key is missing or malformed.
    """
    key = _settings.encryption_key
    if not key:
        raise EncryptionError(message="ENCRYPTION_KEY environment variable is not set.")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise EncryptionError(
            message="Invalid ENCRYPTION_KEY. Generate one with Fernet.generate_key()."
        ) from exc


def encrypt(plain_text: str) -> str:
    """
    Encrypt a plain-text string.

    Args:
        plain_text: The sensitive string to encrypt (e.g., a database password).

    Returns:
        URL-safe base64-encoded ciphertext string.

    Raises:
        EncryptionError: If encryption fails.
    """
    try:
        fernet = _get_fernet()
        ciphertext = fernet.encrypt(plain_text.encode("utf-8"))
        return ciphertext.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(message="Failed to encrypt data.") from exc


def decrypt(cipher_text: str) -> str:
    """
    Decrypt a Fernet-encrypted ciphertext string.

    Args:
        cipher_text: The encrypted string previously produced by encrypt().

    Returns:
        The original plain-text string.

    Raises:
        EncryptionError: If decryption fails (bad key, tampered ciphertext, expired token).
    """
    try:
        fernet = _get_fernet()
        plain_bytes = fernet.decrypt(cipher_text.encode("utf-8"))
        return plain_bytes.decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError(
            message="Failed to decrypt data. The ciphertext may be corrupted or the key has changed."
        ) from exc
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(message="Failed to decrypt data.") from exc


def encrypt_dict(data: dict[str, str]) -> dict[str, str]:
    """
    Encrypt all values in a dictionary.

    Useful for encrypting an entire credentials dict before storing in the DB.

    Args:
        data: Dictionary with string keys and string values.

    Returns:
        New dictionary with the same keys but encrypted values.
    """
    return {key: encrypt(value) for key, value in data.items()}


def decrypt_dict(data: dict[str, str]) -> dict[str, str]:
    """
    Decrypt all values in a dictionary.

    Args:
        data: Dictionary with encrypted string values.

    Returns:
        New dictionary with decrypted string values.
    """
    return {key: decrypt(value) for key, value in data.items()}
