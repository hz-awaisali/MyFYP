"""Department and Program repositories."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.departments.models import Department, Program


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def get_with_programs(self, id_) -> Department | None:
        stmt = (
            select(Department)
            .where(Department.id == id_)
            .options(selectinload(Department.programs))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(self, *, offset, limit, term=None):
        stmt = select(Department).options(selectinload(Department.programs))
        count_stmt = select(func.count()).select_from(Department)
        if term:
            like = f"%{term}%"
            stmt = stmt.where(Department.name.ilike(like))
            count_stmt = count_stmt.where(Department.name.ilike(like))
        stmt = stmt.order_by(Department.name).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total


class ProgramRepository(BaseRepository[Program]):
    model = Program

    async def list_by_department(self, department_id) -> list[Program]:
        stmt = (
            select(Program)
            .where(Program.department_id == department_id)
            .order_by(Program.name)
        )
        return list((await self.session.execute(stmt)).scalars().all())
