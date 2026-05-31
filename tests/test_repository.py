"""Repository / service CRUD tests."""

import pytest

from app.departments.schemas import DepartmentCreate, ProgramCreate
from app.departments.service import DepartmentService

pytestmark = pytest.mark.asyncio


async def test_department_crud(db):
    service = DepartmentService(db)
    dept = await service.create(DepartmentCreate(name="CS & IT", code="csit"))
    assert dept.code == "CSIT"

    fetched = await service.get(dept.id)
    assert fetched.name == "CS & IT"

    program = await service.add_program(
        dept.id, ProgramCreate(name="BS Computer Science", code="bscs", duration_years=4)
    )
    assert program.code == "BSCS"

    programs = await service.list_programs(dept.id)
    assert len(programs) == 1


async def test_department_list_pagination(db):
    service = DepartmentService(db)
    for i in range(3):
        await service.create(DepartmentCreate(name=f"Dept {i}", code=f"D{i}"))
    items, total = await service.list(offset=0, limit=2)
    assert total == 3
    assert len(items) == 2
