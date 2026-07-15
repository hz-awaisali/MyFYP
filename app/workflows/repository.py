"""Workflow repositories."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.workflows.models import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStep,
)


class WorkflowDefinitionRepository(BaseRepository[WorkflowDefinition]):
    model = WorkflowDefinition

    async def get_with_steps(self, id_) -> WorkflowDefinition | None:
        stmt = (
            select(WorkflowDefinition)
            .where(WorkflowDefinition.id == id_)
            .options(selectinload(WorkflowDefinition.steps))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(self, *, offset, limit, term=None):
        stmt = select(WorkflowDefinition).options(selectinload(WorkflowDefinition.steps))
        count_stmt = select(func.count()).select_from(WorkflowDefinition)
        if term:
            like = f"%{term}%"
            stmt = stmt.where(WorkflowDefinition.name.ilike(like))
            count_stmt = count_stmt.where(WorkflowDefinition.name.ilike(like))
        stmt = stmt.order_by(WorkflowDefinition.name).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total


class WorkflowStepRepository(BaseRepository[WorkflowStep]):
    model = WorkflowStep

    async def list_for_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowStep]:
        stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.step_order)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def next_step(self, workflow_id: uuid.UUID, current_order: int) -> WorkflowStep | None:
        stmt = (
            select(WorkflowStep)
            .where(
                WorkflowStep.workflow_id == workflow_id,
                WorkflowStep.step_order > current_order,
            )
            .order_by(WorkflowStep.step_order)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class WorkflowInstanceRepository(BaseRepository[WorkflowInstance]):
    model = WorkflowInstance

    async def get_by_application(self, application_id: uuid.UUID) -> WorkflowInstance | None:
        stmt = (
            select(WorkflowInstance)
            .where(WorkflowInstance.application_id == application_id)
            .options(
                selectinload(WorkflowInstance.actions).selectinload(WorkflowAction.actor),
                selectinload(WorkflowInstance.actions).selectinload(WorkflowAction.step),
                selectinload(WorkflowInstance.current_step),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class WorkflowActionRepository(BaseRepository[WorkflowAction]):
    model = WorkflowAction
