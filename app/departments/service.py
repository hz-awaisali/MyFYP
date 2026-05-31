"""Department and Program services."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.departments.models import Department, Program
from app.departments.repository import DepartmentRepository, ProgramRepository
from app.departments.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    ProgramCreate,
    ProgramUpdate,
)


class DepartmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DepartmentRepository(session)
        self.programs = ProgramRepository(session)

    async def get(self, department_id: uuid.UUID) -> Department:
        dept = await self.repo.get_with_programs(department_id)
        if dept is None:
            raise NotFoundError("Department not found")
        return dept

    async def list(self, *, offset, limit, term=None):
        return await self.repo.list_paginated(offset=offset, limit=limit, term=term)

    async def create(self, data: DepartmentCreate) -> Department:
        if await self.repo.get_by(code=data.code.upper()):
            raise ConflictError("Department code already exists")
        dept = Department(
            name=data.name,
            code=data.code.upper(),
            description=data.description,
            hod_id=data.hod_id,
        )
        await self.repo.add(dept)
        await self.session.commit()
        return await self.repo.get_with_programs(dept.id)

    async def update(self, department_id: uuid.UUID, data: DepartmentUpdate) -> Department:
        dept = await self.get(department_id)
        payload = data.model_dump(exclude_unset=True)
        if "code" in payload and payload["code"]:
            payload["code"] = payload["code"].upper()
        for key, value in payload.items():
            setattr(dept, key, value)
        await self.session.commit()
        return await self.repo.get_with_programs(dept.id)

    async def delete(self, department_id: uuid.UUID) -> None:
        dept = await self.get(department_id)
        await self.repo.delete(dept)
        await self.session.commit()

    # --- Programs ---
    async def add_program(self, department_id: uuid.UUID, data: ProgramCreate) -> Program:
        await self.get(department_id)  # ensure department exists
        if await self.programs.get_by(code=data.code.upper()):
            raise ConflictError("Program code already exists")
        program = Program(
            name=data.name,
            code=data.code.upper(),
            description=data.description,
            duration_years=data.duration_years,
            department_id=department_id,
        )
        await self.programs.add(program)
        await self.session.commit()
        return program

    async def list_programs(self, department_id: uuid.UUID) -> list[Program]:
        await self.get(department_id)
        return await self.programs.list_by_department(department_id)

    async def update_program(self, program_id: uuid.UUID, data: ProgramUpdate) -> Program:
        program = await self.programs.get(program_id)
        if program is None:
            raise NotFoundError("Program not found")
        payload = data.model_dump(exclude_unset=True)
        if "code" in payload and payload["code"]:
            payload["code"] = payload["code"].upper()
        for key, value in payload.items():
            setattr(program, key, value)
        await self.session.commit()
        return program

    async def delete_program(self, program_id: uuid.UUID) -> None:
        program = await self.programs.get(program_id)
        if program is None:
            raise NotFoundError("Program not found")
        await self.programs.delete(program)
        await self.session.commit()
