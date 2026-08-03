"""Authentication API Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, Token
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new Tenant and Admin User."""
    service = AuthService(db)
    user, _ = await service.register(req)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate User and return JWT access and refresh tokens."""
    service = AuthService(db)
    return await service.login(req)


@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Rotate Refresh Token and issue new Access Token."""
    service = AuthService(db)
    return await service.refresh_tokens(req.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Revoke Refresh Token."""
    service = AuthService(db)
    await service.logout(req.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserRead.model_validate(current_user)
