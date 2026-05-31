"""User management endpoints (admin) and self-service profile."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserStatus
from app.common.schemas import Page
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permissions
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.users.schemas import (
    AdminCreateUser,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
)
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserRead])
async def list_users(
    pagination: PaginationParams = Depends(pagination_params),
    status: UserStatus | None = Query(None),
    role_id: uuid.UUID | None = Query(None),
    department_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_users")),
):
    items, total = await UserService(db).list_users(
        offset=pagination.offset,
        limit=pagination.limit,
        status=status,
        role_id=role_id,
        department_id=department_id,
        term=pagination.search,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    data: AdminCreateUser,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_users")),
):
    return await UserService(db).create_user(data)


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    # Users cannot reassign their own department via self-service.
    safe = data.model_copy(update={"department_id": None})
    return await UserService(db).update_user(current_user.id, safe)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_users")),
):
    return await UserService(db).get(user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_users")),
):
    return await UserService(db).update_user(user_id, data)


@router.patch("/{user_id}/status", response_model=UserRead)
async def change_user_status(
    user_id: uuid.UUID,
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_users")),
):
    """Approve / reject / suspend a user account."""
    return await UserService(db).change_status(user_id, data)
