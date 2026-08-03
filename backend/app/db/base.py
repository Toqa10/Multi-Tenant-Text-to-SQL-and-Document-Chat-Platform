"""
SQLAlchemy declarative base and shared mixins.

All ORM models must import Base from this module.
Mixins provide reusable columns (UUID PK, timestamps) to avoid duplication.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base class for all SQLAlchemy models.

    All models inherit from this class. Alembic uses it for autogenerate.
    """

    type_annotation_map: dict[type, Any] = {}


class UUIDMixin:
    """
    Provides a UUID primary key column.

    The default value is generated server-side by PostgreSQL using gen_random_uuid()
    which avoids round-trips but also works when the value is provided from Python.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


class TimestampMixin:
    """
    Provides created_at and updated_at columns with automatic management.

    - created_at: Set once at INSERT time.
    - updated_at: Updated automatically on every UPDATE.
    Both are stored in UTC.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditableMixin(UUIDMixin, TimestampMixin):
    """
    Convenience mixin that combines UUID PK + timestamps.

    Use this on every model that requires both (which is almost all models).
    """

    pass
