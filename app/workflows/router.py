"""Workflow configuration endpoints."""

import uuid

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Message, Page
from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.workflows.schemas import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionRead,
    WorkflowDefinitionUpdate,
    WorkflowStepCreate,
    WorkflowStepRead,
)
from app.workflows.service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflow Engine"])


@router.get("", response_model=Page[WorkflowDefinitionRead])
async def list_workflows(
    pagination: PaginationParams = Depends(pagination_params),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    items, total = await WorkflowService(db).list(
        offset=pagination.offset, limit=pagination.limit, term=pagination.search
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.post("", response_model=WorkflowDefinitionRead, status_code=201)
async def create_workflow(
    data: WorkflowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    return await WorkflowService(db).create(data)


@router.get("/{workflow_id}", response_model=WorkflowDefinitionRead)
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    return await WorkflowService(db).get(workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowDefinitionRead)
async def update_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    return await WorkflowService(db).update(workflow_id, data)


@router.delete("/{workflow_id}", response_model=Message)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    await WorkflowService(db).delete(workflow_id)
    return Message(message="Workflow deleted")


@router.post("/{workflow_id}/steps", response_model=WorkflowStepRead, status_code=201)
async def add_step(
    workflow_id: uuid.UUID,
    data: WorkflowStepCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    return await WorkflowService(db).add_step(workflow_id, data)


@router.post("/{workflow_id}/reorder", response_model=WorkflowDefinitionRead)
async def reorder_steps(
    workflow_id: uuid.UUID,
    ordered_step_ids: list[uuid.UUID] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    return await WorkflowService(db).reorder_steps(workflow_id, ordered_step_ids)


@router.delete("/steps/{step_id}", response_model=Message)
async def delete_step(
    step_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_workflows")),
):
    await WorkflowService(db).delete_step(step_id)
    return Message(message="Step deleted")
