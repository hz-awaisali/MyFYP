"""User schemas."""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.common.enums import UserStatus
from app.common.schemas import ORMBase
from app.roles.schemas import RoleRead


class StudentProfileRead(ORMBase):
    id: uuid.UUID
    registration_number: str
    program_id: uuid.UUID | None = None
    semester: int | None = None
    batch: str | None = None


class UserRead(ORMBase):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None = None
    status: UserStatus
    is_active: bool
    role_id: uuid.UUID
    department_id: uuid.UUID | None = None
    role: RoleRead | None = None
    student_profile: StudentProfileRead | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    department_id: uuid.UUID | None = None


class UserStatusUpdate(BaseModel):
    status: UserStatus


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    role_name: str
    department_id: uuid.UUID | None = None
    status: UserStatus = UserStatus.APPROVED
