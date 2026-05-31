"""Department and Program endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Message, Page
from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.departments.schemas import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
)
from app.departments.service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments & Programs"])


@router.get("", response_model=Page[DepartmentRead])
async def list_departments(
    pagination: PaginationParams = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
):
    items, total = await DepartmentService(db).list(
        offset=pagination.offset, limit=pagination.limit, term=pagination.search
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    return await DepartmentService(db).create(data)


@router.get("/{department_id}", response_model=DepartmentRead)
async def get_department(department_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await DepartmentService(db).get(department_id)


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: uuid.UUID,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    return await DepartmentService(db).update(department_id, data)


@router.delete("/{department_id}", response_model=Message)
async def delete_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    await DepartmentService(db).delete(department_id)
    return Message(message="Department deleted")


@router.get("/{department_id}/programs", response_model=list[ProgramRead])
async def list_programs(department_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await DepartmentService(db).list_programs(department_id)


@router.post("/{department_id}/programs", response_model=ProgramRead, status_code=201)
async def add_program(
    department_id: uuid.UUID,
    data: ProgramCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    return await DepartmentService(db).add_program(department_id, data)


@router.patch("/programs/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: uuid.UUID,
    data: ProgramUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    return await DepartmentService(db).update_program(program_id, data)


@router.delete("/programs/{program_id}", response_model=Message)
async def delete_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_departments")),
):
    await DepartmentService(db).delete_program(program_id)
    return Message(message="Program deleted")
