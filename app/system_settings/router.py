"""System settings endpoints (super admin / settings managers)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permissions
from app.system_settings.schemas import SettingRead, SettingUpsert
from app.system_settings.service import SystemSettingService

router = APIRouter(prefix="/system-settings", tags=["System Settings"])


@router.get("", response_model=list[SettingRead])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_settings")),
):
    return await SystemSettingService(db).list()


@router.put("", response_model=SettingRead)
async def upsert_setting(
    data: SettingUpsert,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_settings")),
):
    return await SystemSettingService(db).upsert(data)
