"""Repositories for roles and permissions."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.roles.models import Permission, Role


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.name == name)
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def get_by_code(self, code: str) -> Permission | None:
        return await self.get_by(code=code)
