"""Application module schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import ApplicationStatus, FieldType, WorkflowActionType
from app.common.schemas import ORMBase


# --- Fields ---
class FieldCreate(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    field_type: FieldType
    is_required: bool = False
    default_value: str | None = None
    validation: dict[str, Any] | None = None
    options: list[Any] | None = None
    display_order: int = 0
    visibility_rule: dict[str, Any] | None = None


class FieldRead(ORMBase):
    id: uuid.UUID
    form_id: uuid.UUID
    key: str
    label: str
    field_type: FieldType
    is_required: bool
    default_value: str | None = None
    validation: dict[str, Any] | None = None
    options: list[Any] | None = None
    display_order: int
    visibility_rule: dict[str, Any] | None = None


# --- Forms ---
class FormCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    fields: list[FieldCreate] = []


class FormRead(ORMBase):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    version: int
    is_active: bool
    fields: list[FieldRead] = []


# --- Categories ---
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    department_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    department_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    is_enabled: bool | None = None


class CategoryRead(ORMBase):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_enabled: bool
    department_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None


class CategoryDetail(CategoryRead):
    forms: list[FormRead] = []


# --- Applications ---
class ResponseInput(BaseModel):
    field_key: str
    value: Any | None = None


class ApplicationCreate(BaseModel):
    category_id: uuid.UUID
    subject: str | None = Field(None, max_length=255)
    responses: list[ResponseInput] = []


class ApplicationResponseRead(ORMBase):
    id: uuid.UUID
    field_id: uuid.UUID
    field_key: str
    value: str | None = None


class ApplicationRead(ORMBase):
    id: uuid.UUID
    category_id: uuid.UUID
    form_id: uuid.UUID | None = None
    student_id: uuid.UUID
    department_id: uuid.UUID | None = None
    status: ApplicationStatus
    subject: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    responses: list[ApplicationResponseRead] = []


class ApplicationActionInput(BaseModel):
    action: WorkflowActionType
    remarks: str | None = None
