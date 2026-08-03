"""
Alembic environment configuration.

Supports both online (running against a live DB) and offline (generating SQL scripts) modes.
Uses the sync engine for Alembic since Alembic doesn't support asyncpg natively.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can detect them
from app.db.base import Base  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.role import Role, Permission, RolePermission  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.database_connection import DatabaseConnection  # noqa: F401
from app.models.schema_metadata import SchemaMetadata  # noqa: F401
from app.models.table_permission import TablePermission  # noqa: F401
from app.models.column_permission import ColumnPermission  # noqa: F401
from app.models.row_filter import RowFilter  # noqa: F401
from app.models.knowledge_base import KnowledgeBase, Document  # noqa: F401
from app.models.document_chunk import DocumentChunk  # noqa: F401
from app.models.conversation import Conversation, Message  # noqa: F401
from app.models.query_log import QueryLog  # noqa: F401
from app.core.config import get_settings

settings = get_settings()

# Alembic Config object
config = context.config

# Configure Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use our application's declarative base for autogenerate support
target_metadata = Base.metadata

# Override the sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.db.async_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """Execute migrations within a transaction."""
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations asynchronously using asyncpg."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, connecting to the database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
