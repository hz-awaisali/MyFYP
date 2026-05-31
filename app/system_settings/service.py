"""System settings service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.system_settings.models import SystemSetting
from app.system_settings.schemas import SettingUpsert


class SystemSettingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self) -> list[SystemSetting]:
        stmt = select(SystemSetting).order_by(SystemSetting.key)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, key: str) -> SystemSetting | None:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert(self, data: SettingUpsert) -> SystemSetting:
        setting = await self.get(data.key)
        if setting is None:
            setting = SystemSetting(key=data.key, value=data.value, description=data.description)
            self.session.add(setting)
        else:
            setting.value = data.value
            if data.description is not None:
                setting.description = data.description
        await self.session.commit()
        return setting
