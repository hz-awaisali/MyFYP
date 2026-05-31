"""Workflow definition management service (admin configuration)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.workflows.models import WorkflowDefinition, WorkflowStep
from app.workflows.repository import (
    WorkflowDefinitionRepository,
    WorkflowStepRepository,
)
from app.workflows.schemas import (
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowStepCreate,
)


class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.definitions = WorkflowDefinitionRepository(session)
        self.steps = WorkflowStepRepository(session)

    async def get(self, workflow_id: uuid.UUID) -> WorkflowDefinition:
        wf = await self.definitions.get_with_steps(workflow_id)
        if wf is None:
            raise NotFoundError("Workflow not found")
        return wf

    async def list(self, *, offset, limit, term=None):
        return await self.definitions.list_paginated(offset=offset, limit=limit, term=term)

    async def create(self, data: WorkflowDefinitionCreate) -> WorkflowDefinition:
        wf = WorkflowDefinition(name=data.name, description=data.description)
        await self.definitions.add(wf)
        for step in data.steps:
            self.session.add(self._build_step(wf.id, step))
        await self.session.commit()
        return await self.definitions.get_with_steps(wf.id)

    async def update(self, workflow_id: uuid.UUID, data: WorkflowDefinitionUpdate) -> WorkflowDefinition:
        wf = await self.get(workflow_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(wf, key, value)
        await self.session.commit()
        return await self.definitions.get_with_steps(wf.id)

    async def delete(self, workflow_id: uuid.UUID) -> None:
        wf = await self.get(workflow_id)
        await self.definitions.delete(wf)
        await self.session.commit()

    @staticmethod
    def _build_step(workflow_id: uuid.UUID, step: WorkflowStepCreate) -> WorkflowStep:
        return WorkflowStep(
            workflow_id=workflow_id,
            step_order=step.step_order,
            name=step.name,
            role_id=step.role_id,
            department_id=step.department_id,
            approval_required=step.approval_required,
            can_forward=step.can_forward,
            can_return=step.can_return,
            can_reject=step.can_reject,
            is_final=step.is_final,
        )

    async def add_step(self, workflow_id: uuid.UUID, step: WorkflowStepCreate) -> WorkflowStep:
        await self.get(workflow_id)
        obj = self._build_step(workflow_id, step)
        await self.steps.add(obj)
        await self.session.commit()
        return obj

    async def reorder_steps(self, workflow_id: uuid.UUID, ordered_step_ids: list[uuid.UUID]) -> WorkflowDefinition:
        wf = await self.get(workflow_id)
        steps_by_id = {s.id: s for s in wf.steps}
        if set(ordered_step_ids) != set(steps_by_id.keys()):
            raise ValidationError("ordered_step_ids must contain exactly the workflow's steps")
        for index, step_id in enumerate(ordered_step_ids, start=1):
            steps_by_id[step_id].step_order = index
        await self.session.commit()
        return await self.definitions.get_with_steps(workflow_id)

    async def delete_step(self, step_id: uuid.UUID) -> None:
        step = await self.steps.get(step_id)
        if step is None:
            raise NotFoundError("Workflow step not found")
        await self.steps.delete(step)
        await self.session.commit()
