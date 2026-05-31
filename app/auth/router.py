"""Authentication endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.auth.service import AuthService
from app.common.schemas import Message
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new student account (created in PENDING status until approved)."""
    user = await AuthService(db).register_student(data)
    return user


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, tokens = await AuthService(db).authenticate(data.email, data.password)
    return AuthResponse(user=user, tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).refresh(data.refresh_token)


@router.post("/logout", response_model=Message)
async def logout(_: CurrentUser):
    """Stateless logout. Clients should discard their tokens.

    (Token revocation/blacklist can be layered in later via Redis.)
    """
    return Message(message="Logged out successfully")


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return current_user
