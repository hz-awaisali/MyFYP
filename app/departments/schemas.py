"""Department and Program schemas."""

import uuid

from pydantic import BaseModel, Field

from app.common.schemas import ORMBase


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None
    duration_years: int | None = Field(None, ge=1, le=10)


class ProgramUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    code: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    duration_years: int | None = Field(None, ge=1, le=10)
    is_active: bool | None = None


class ProgramRead(ORMBase):
    id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    duration_years: int | None = None
    is_active: bool
    department_id: uuid.UUID


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None
    hod_id: uuid.UUID | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    code: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = None
    hod_id: uuid.UUID | None = None
    is_active: bool | None = None


class DepartmentRead(ORMBase):
    id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    is_active: bool
    hod_id: uuid.UUID | None = None
    programs: list[ProgramRead] = []
