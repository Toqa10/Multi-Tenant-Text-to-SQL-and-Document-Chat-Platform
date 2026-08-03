"""Tenant model — top-level isolation boundary."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, AuditableMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.database_connection import DatabaseConnection
    from app.models.knowledge_base import KnowledgeBase
    from app.models.audit_log import AuditLog


class Tenant(Base, AuditableMixin):
    """
    Represents an organization / customer account.

    Every resource in the system belongs to exactly one Tenant.
    The tenant_id is always extracted from the JWT and injected into
    every repository query — data leakage between tenants is impossible
    by design.
    """

    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_tenants_slug"),
        CheckConstraint("char_length(slug) >= 2", name="ck_tenants_slug_min_length"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free", server_default="free"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    database_connections: Mapped[list["DatabaseConnection"]] = relationship(
        "DatabaseConnection", back_populates="tenant", cascade="all, delete-orphan"
    )
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="tenant", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"
