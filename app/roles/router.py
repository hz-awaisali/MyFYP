"""Read-only role/permission endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permissions
from app.roles.repository import PermissionRepository, RoleRepository
from app.roles.schemas import PermissionRead, RoleRead

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get("", response_model=list[RoleRead])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_roles")),
):
    return await RoleRepository(db).list_all()


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_roles")),
):
    repo = PermissionRepository(db)
    return await repo.list(limit=500, order_by=None)
