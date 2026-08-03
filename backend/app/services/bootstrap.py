"""Superadmin and initial system permissions bootstrap service."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.role import Permission
from app.repositories.role import PermissionRepository, RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository

logger = structlog.get_logger(__name__)
settings = get_settings()

DEFAULT_PERMISSIONS = [
    ("connection", "create", "Create database connections"),
    ("connection", "read", "View database connections"),
    ("connection", "update", "Edit database connections"),
    ("connection", "delete", "Delete database connections"),
    ("connection", "test", "Test database connectivity"),
    ("connection", "sync", "Synchronize database schema metadata"),
    ("permission", "manage", "Manage table, column, and row permissions"),
    ("knowledge_base", "create", "Create knowledge bases"),
    ("knowledge_base", "read", "View knowledge bases"),
    ("knowledge_base", "delete", "Delete knowledge bases"),
    ("document", "upload", "Upload documents"),
    ("document", "delete", "Delete documents"),
    ("conversation", "create", "Start chat conversations"),
    ("conversation", "read", "View conversation history"),
    ("conversation", "delete", "Delete conversations"),
    ("user", "manage", "Manage tenant users"),
    ("role", "manage", "Manage tenant roles"),
]


class BootstrapService:
    """Initializes platform system permissions and superadmin user/tenant on first run."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tenant_repo = TenantRepository(session)
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.perm_repo = PermissionRepository(session)

    async def run(self) -> None:
        """Run bootstrap initialization."""
        # 1. Seed global atomic permissions
        existing_perms = await self.perm_repo.list_all()
        existing_map = {(p.resource, p.action) for p in existing_perms}

        for res, act, desc in DEFAULT_PERMISSIONS:
            if (res, act) not in existing_map:
                await self.perm_repo.create(
                    name=f"{res}:{act}", resource=res, action=act, description=desc
                )

        # 2. Bootstrap Superadmin Tenant & User
        tenant = await self.tenant_repo.get_by_slug(settings.superadmin_tenant_slug)
        if not tenant:
            tenant = await self.tenant_repo.create(
                name=settings.superadmin_tenant_name,
                slug=settings.superadmin_tenant_slug,
                plan="enterprise",
            )
            logger.info("Created superadmin tenant", slug=tenant.slug)

        user = await self.user_repo.get_by_email_and_tenant(
            settings.superadmin_email, tenant.id
        )
        if not user:
            admin_role = await self.role_repo.get_by_name_and_tenant("Admin", tenant.id)
            if not admin_role:
                admin_role = await self.role_repo.create(
                    tenant_id=tenant.id,
                    name="Admin",
                    description="Superadmin role",
                )
                # Assign all permissions
                all_perms = await self.perm_repo.list_all()
                admin_role.permissions.extend(all_perms)

            user = await self.user_repo.create(
                tenant_id=tenant.id,
                email=settings.superadmin_email.lower(),
                hashed_password=hash_password(settings.superadmin_password),
                full_name="Platform Administrator",
                is_active=True,
                is_superuser=True,
            )
            user.roles.append(admin_role)
            await self.session.flush()
            logger.info("Created superadmin user", email=user.email)
