"""
Domain exception hierarchy.

All application exceptions inherit from PlatformException so that
the global exception handler in main.py can catch them in one place
and return structured JSON error responses without leaking stack traces.
"""

from __future__ import annotations

from typing import Any


class PlatformException(Exception):
    """Base exception for all platform-specific errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        super().__init__(self.message)


# ─────────────────────────────────────────────────────────────
# Authentication & Authorization
# ─────────────────────────────────────────────────────────────


class AuthenticationError(PlatformException):
    """Raised when authentication credentials are invalid or missing."""

    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication failed. Please provide valid credentials."


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    error_code = "TOKEN_EXPIRED"
    message = "Your session has expired. Please log in again."


class TokenInvalidError(AuthenticationError):
    """Raised when a JWT token is malformed or has an invalid signature."""

    error_code = "TOKEN_INVALID"
    message = "The provided token is invalid."


class RefreshTokenRevokedError(AuthenticationError):
    """Raised when an attempt is made to use a revoked refresh token."""

    error_code = "REFRESH_TOKEN_REVOKED"
    message = "This refresh token has been revoked. Please log in again."


class PermissionDeniedError(PlatformException):
    """Raised when the authenticated user lacks the required permission."""

    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class TenantIsolationError(PlatformException):
    """Raised when cross-tenant data access is detected or blocked."""

    status_code = 403
    error_code = "TENANT_ISOLATION_VIOLATED"
    message = "Access to resources outside your tenant is not permitted."


# ─────────────────────────────────────────────────────────────
# Resource Errors
# ─────────────────────────────────────────────────────────────


class NotFoundError(PlatformException):
    """Raised when a requested resource does not exist."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(PlatformException):
    """Raised when a resource creation violates a uniqueness constraint."""

    status_code = 409
    error_code = "CONFLICT"
    message = "A resource with the given identifier already exists."


class ValidationError(PlatformException):
    """Raised when request data fails business-level validation."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "The provided data failed validation."


# ─────────────────────────────────────────────────────────────
# Database Connection Errors
# ─────────────────────────────────────────────────────────────


class ConnectionError(PlatformException):
    """Raised when a customer database connection cannot be established."""

    status_code = 502
    error_code = "DATABASE_CONNECTION_FAILED"
    message = "Failed to connect to the external database."


class ConnectionTimeoutError(ConnectionError):
    """Raised when a database connection attempt times out."""

    error_code = "DATABASE_CONNECTION_TIMEOUT"
    message = "The database connection attempt timed out."


class UnsupportedDatabaseTypeError(PlatformException):
    """Raised when an unsupported database adapter type is requested."""

    status_code = 400
    error_code = "UNSUPPORTED_DATABASE_TYPE"
    message = "The specified database type is not supported."


class SchemaDiscoveryError(PlatformException):
    """Raised when schema introspection fails on a customer database."""

    status_code = 502
    error_code = "SCHEMA_DISCOVERY_FAILED"
    message = "Failed to discover the database schema."


# ─────────────────────────────────────────────────────────────
# SQL Security Errors
# ─────────────────────────────────────────────────────────────


class SQLSecurityError(PlatformException):
    """Raised when generated SQL violates security rules."""

    status_code = 400
    error_code = "SQL_SECURITY_VIOLATION"
    message = "The generated SQL query violates security policy and cannot be executed."


class SQLValidationError(PlatformException):
    """Raised when generated SQL fails syntactic or structural validation."""

    status_code = 400
    error_code = "SQL_VALIDATION_FAILED"
    message = "The generated SQL query failed validation."


class SQLExecutionError(PlatformException):
    """Raised when a validated SQL query fails during execution."""

    status_code = 500
    error_code = "SQL_EXECUTION_FAILED"
    message = "The SQL query failed during execution."


class SQLTimeoutError(SQLExecutionError):
    """Raised when a SQL query exceeds the configured execution timeout."""

    error_code = "SQL_TIMEOUT"
    message = "The SQL query exceeded the maximum allowed execution time."


class SQLResultTooLargeError(SQLExecutionError):
    """Raised when a SQL query returns more rows than the configured limit."""

    error_code = "SQL_RESULT_TOO_LARGE"
    message = "The query returned too many rows. Please refine your question."


# ─────────────────────────────────────────────────────────────
# Document & RAG Errors
# ─────────────────────────────────────────────────────────────


class DocumentProcessingError(PlatformException):
    """Raised when document parsing or embedding fails."""

    status_code = 500
    error_code = "DOCUMENT_PROCESSING_FAILED"
    message = "Failed to process the uploaded document."


class UnsupportedFileTypeError(PlatformException):
    """Raised when an uploaded file has an unsupported MIME type or extension."""

    status_code = 415
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "The uploaded file type is not supported."


class FileTooLargeError(PlatformException):
    """Raised when an uploaded file exceeds the maximum allowed size."""

    status_code = 413
    error_code = "FILE_TOO_LARGE"
    message = "The uploaded file exceeds the maximum allowed size."


class StorageError(PlatformException):
    """Raised when an object storage operation fails."""

    status_code = 500
    error_code = "STORAGE_ERROR"
    message = "A storage operation failed. Please try again."


# ─────────────────────────────────────────────────────────────
# Agent / LLM Errors
# ─────────────────────────────────────────────────────────────


class AgentError(PlatformException):
    """Raised when a LangGraph agent encounters an unrecoverable error."""

    status_code = 500
    error_code = "AGENT_ERROR"
    message = "The AI agent encountered an error. Please try again."


class LLMError(AgentError):
    """Raised when the LLM API call fails."""

    error_code = "LLM_API_ERROR"
    message = "The language model API call failed. Please try again."


class IntentClassificationError(AgentError):
    """Raised when intent classification cannot determine the query type."""

    error_code = "INTENT_CLASSIFICATION_FAILED"
    message = "Could not determine the intent of your question. Please rephrase it."


# ─────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────


class RateLimitExceededError(PlatformException):
    """Raised when a client exceeds the configured request rate limit."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please slow down and try again later."
