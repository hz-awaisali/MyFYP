"""Workflow schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import WorkflowActionType
from app.common.schemas import ORMBase


class WorkflowStepCreate(BaseModel):
    step_order: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=150)
    role_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    approval_required: bool = True
    can_forward: bool = True
    can_return: bool = True
    can_reject: bool = True
    is_final: bool = False


class WorkflowStepRead(ORMBase):
    id: uuid.UUID
    workflow_id: uuid.UUID
    step_order: int
    name: str
    role_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    approval_required: bool
    can_forward: bool
    can_return: bool
    can_reject: bool
    is_final: bool


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    steps: list[WorkflowStepCreate] = []


class WorkflowDefinitionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class WorkflowDefinitionRead(ORMBase):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_active: bool
    steps: list[WorkflowStepRead] = []


class ActorRead(ORMBase):
    id: uuid.UUID
    full_name: str
    email: str


class WorkflowActionRead(ORMBase):
    id: uuid.UUID
    instance_id: uuid.UUID
    step_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: WorkflowActionType
    remarks: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    created_at: datetime
    actor: ActorRead | None = None
    step: WorkflowStepRead | None = None



class WorkflowInstanceRead(ORMBase):
    id: uuid.UUID
    workflow_id: uuid.UUID
    application_id: uuid.UUID
    current_step_id: uuid.UUID | None = None
    is_complete: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actions: list[WorkflowActionRead] = []
