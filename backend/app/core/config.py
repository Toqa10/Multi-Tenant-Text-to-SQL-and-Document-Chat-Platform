"""
Core application configuration using Pydantic Settings v2.

All settings are loaded from environment variables (or .env file).
Never hard-code secrets — use this module exclusively.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL application database configuration."""

    host: str = Field(default="localhost", alias="DATABASE_HOST")
    port: int = Field(default=5432, alias="DATABASE_PORT")
    name: str = Field(default="texttosql_db", alias="DATABASE_NAME")
    user: str = Field(default="texttosql_user", alias="DATABASE_USER")
    password: str = Field(alias="DATABASE_PASSWORD")
    pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=40, alias="DATABASE_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def async_url(self) -> str:
        """Async SQLAlchemy DSN using asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        """Sync SQLAlchemy DSN using psycopg2 driver (used by Alembic)."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")
    max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL_SECONDS")
    schema_cache_ttl: int = Field(default=86400, alias="REDIS_SCHEMA_CACHE_TTL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def url(self) -> str:
        """Redis connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class MinIOSettings(BaseSettings):
    """MinIO object storage configuration."""

    endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    access_key: str = Field(alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(alias="MINIO_SECRET_KEY")
    secure: bool = Field(default=False, alias="MINIO_SECURE")
    region: str = Field(default="us-east-1", alias="MINIO_REGION")
    presigned_url_expiry: int = Field(default=3600, alias="MINIO_PRESIGNED_URL_EXPIRY_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class CelerySettings(BaseSettings):
    """Celery task queue configuration."""

    broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")
    worker_concurrency: int = Field(default=4, alias="CELERY_WORKER_CONCURRENCY")
    task_max_retries: int = Field(default=3, alias="CELERY_TASK_MAX_RETRIES")
    task_retry_delay: int = Field(default=60, alias="CELERY_TASK_RETRY_DELAY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class OpenAISettings(BaseSettings):
    """OpenAI API configuration."""

    api_key: str = Field(alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    max_tokens: int = Field(default=4096, alias="OPENAI_MAX_TOKENS")
    temperature: float = Field(default=0.0, alias="OPENAI_TEMPERATURE")
    timeout_seconds: int = Field(default=60, alias="OPENAI_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class SQLSettings(BaseSettings):
    """Text-to-SQL execution settings."""

    query_timeout_seconds: int = Field(default=30, alias="SQL_QUERY_TIMEOUT_SECONDS")
    max_result_rows: int = Field(default=1000, alias="SQL_MAX_RESULT_ROWS")
    max_schema_tables_in_context: int = Field(default=50, alias="SQL_MAX_SCHEMA_TABLES_IN_CONTEXT")
    max_retries: int = Field(default=3, alias="SQL_MAX_RETRIES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class RAGSettings(BaseSettings):
    """Retrieval-Augmented Generation settings."""

    chunk_size: int = Field(default=1024, alias="RAG_CHUNK_SIZE")
    chunk_overlap: int = Field(default=128, alias="RAG_CHUNK_OVERLAP")
    top_k: int = Field(default=10, alias="RAG_TOP_K")
    reranker_enabled: bool = Field(default=False, alias="RAG_RERANKER_ENABLED")
    reranker_top_k: int = Field(default=5, alias="RAG_RERANKER_TOP_K")
    similarity_threshold: float = Field(default=0.7, alias="RAG_SIMILARITY_THRESHOLD")
    max_file_size_mb: int = Field(default=100, alias="RAG_MAX_FILE_SIZE_MB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def max_file_size_bytes(self) -> int:
        """Maximum allowed file upload size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


class JWTSettings(BaseSettings):
    """JWT token configuration."""

    secret_key: str = Field(alias="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class ObservabilitySettings(BaseSettings):
    """OpenTelemetry and Prometheus configuration."""

    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(
        default="text-to-sql-platform", alias="OTEL_SERVICE_NAME"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Literal["json", "console"] = Field(default="json", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class Settings(BaseSettings):
    """
    Master application settings.

    Sub-settings are loaded as nested models.
    Prefer accessing sub-settings directly:
        settings.db.async_url
        settings.redis.url
    """

    # Application
    app_name: str = Field(default="Text-to-SQL Platform", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(alias="SECRET_KEY")
    allowed_hosts: list[str] = Field(default=["localhost", "127.0.0.1"], alias="ALLOWED_HOSTS")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], alias="CORS_ORIGINS"
    )

    # Encryption key for storing DB credentials
    encryption_key: str = Field(alias="ENCRYPTION_KEY")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_rpm: int = Field(default=60, alias="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_chat_rpm: int = Field(default=20, alias="RATE_LIMIT_CHAT_REQUESTS_PER_MINUTE")

    # Superadmin bootstrap
    superadmin_email: str = Field(
        default="admin@platform.local", alias="SUPERADMIN_EMAIL"
    )
    superadmin_password: str = Field(alias="SUPERADMIN_PASSWORD")
    superadmin_tenant_name: str = Field(
        default="Platform Admin", alias="SUPERADMIN_TENANT_NAME"
    )
    superadmin_tenant_slug: str = Field(
        default="platform-admin", alias="SUPERADMIN_TENANT_SLUG"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.environment == "production"

    @property
    def db(self) -> DatabaseSettings:
        """Database sub-settings."""
        return DatabaseSettings()  # type: ignore[call-arg]

    @property
    def redis(self) -> RedisSettings:
        """Redis sub-settings."""
        return RedisSettings()  # type: ignore[call-arg]

    @property
    def minio(self) -> MinIOSettings:
        """MinIO sub-settings."""
        return MinIOSettings()  # type: ignore[call-arg]

    @property
    def celery(self) -> CelerySettings:
        """Celery sub-settings."""
        return CelerySettings()  # type: ignore[call-arg]

    @property
    def openai(self) -> OpenAISettings:
        """OpenAI sub-settings."""
        return OpenAISettings()  # type: ignore[call-arg]

    @property
    def sql(self) -> SQLSettings:
        """Text-to-SQL sub-settings."""
        return SQLSettings()  # type: ignore[call-arg]

    @property
    def rag(self) -> RAGSettings:
        """RAG sub-settings."""
        return RAGSettings()  # type: ignore[call-arg]

    @property
    def jwt(self) -> JWTSettings:
        """JWT sub-settings."""
        return JWTSettings()  # type: ignore[call-arg]

    @property
    def obs(self) -> ObservabilitySettings:
        """Observability sub-settings."""
        return ObservabilitySettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton settings instance.

    Uses lru_cache so the .env file is parsed only once.
    In tests, call get_settings.cache_clear() to reload.
    """
    return Settings()  # type: ignore[call-arg]


# Convenience alias used throughout the codebase
settings = get_settings()
