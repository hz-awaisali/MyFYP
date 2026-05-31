"""Configurable workflow engine.

The engine interprets workflow definitions/steps at runtime to advance an
application through its approval chain. It is intentionally decoupled from the
applications module: callers pass the application object in and the engine
mutates its status, records a ``WorkflowAction`` and returns the result. The
caller owns the surrounding transaction (commit).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ApplicationStatus, WorkflowActionType
from app.core.exceptions import PermissionDeniedError, ValidationError
from app.workflows.models import WorkflowAction, WorkflowInstance, WorkflowStep
from app.workflows.repository import (
    WorkflowInstanceRepository,
    WorkflowStepRepository,
)


@dataclass
class ActionResult:
    instance: WorkflowInstance
    action: WorkflowAction
    new_status: ApplicationStatus
    is_complete: bool


class WorkflowEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.steps = WorkflowStepRepository(session)
        self.instances = WorkflowInstanceRepository(session)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    async def start(self, *, application_id: uuid.UUID, workflow_id: uuid.UUID) -> WorkflowInstance:
        """Create a workflow instance positioned at the first step."""
        steps = await self.steps.list_for_workflow(workflow_id)
        if not steps:
            raise ValidationError("Assigned workflow has no steps configured")

        instance = WorkflowInstance(
            workflow_id=workflow_id,
            application_id=application_id,
            current_step_id=steps[0].id,
            started_at=self._now(),
        )
        await self.instances.add(instance)
        return instance

    def can_act(self, user, step: WorkflowStep, *, application_department_id: uuid.UUID | None) -> bool:
        """Whether ``user`` is allowed to act on ``step``."""
        if user.is_super_admin:
            return True
        if step.role_id is not None and user.role_id != step.role_id:
            return False
        required_department = step.department_id or application_department_id
        if required_department is not None and user.department_id != required_department:
            return False
        return True

    async def act(
        self,
        *,
        application,
        instance: WorkflowInstance,
        user,
        action: WorkflowActionType,
        remarks: str | None = None,
    ) -> ActionResult:
        """Apply an action to a running workflow instance."""
        if instance.is_complete and action != WorkflowActionType.REOPEN:
            raise ValidationError("Workflow is already complete")

        current_step = (
            await self.steps.get(instance.current_step_id)
            if instance.current_step_id
            else None
        )
        app_department_id = getattr(application, "department_id", None)

        # add_remarks is permitted to any authorized actor on the step.
        if action != WorkflowActionType.REOPEN and current_step is not None:
            if not self.can_act(user, current_step, application_department_id=app_department_id):
                raise PermissionDeniedError("You are not authorized to act on this step")

        from_status = application.status
        new_status = from_status

        if action in (WorkflowActionType.APPROVE, WorkflowActionType.FORWARD):
            new_status = await self._advance(application, instance, current_step)
        elif action == WorkflowActionType.REJECT:
            if current_step and not current_step.can_reject:
                raise ValidationError("Rejection is not allowed at this step")
            new_status = ApplicationStatus.REJECTED
            self._complete(instance)
        elif action == WorkflowActionType.RETURN_FOR_CORRECTION:
            if current_step and not current_step.can_return:
                raise ValidationError("Return is not allowed at this step")
            new_status = ApplicationStatus.RETURNED
        elif action == WorkflowActionType.ADD_REMARKS:
            if not remarks:
                raise ValidationError("Remarks are required for this action")
            new_status = from_status
        elif action == WorkflowActionType.CLOSE:
            new_status = ApplicationStatus.CLOSED
            self._complete(instance)
        elif action == WorkflowActionType.REOPEN:
            new_status = ApplicationStatus.PENDING
            instance.is_complete = False
            instance.completed_at = None
            steps = await self.steps.list_for_workflow(instance.workflow_id)
            instance.current_step_id = steps[0].id if steps else None
        else:
            raise ValidationError(f"Unsupported action: {action}")

        application.status = new_status

        wf_action = WorkflowAction(
            instance_id=instance.id,
            step_id=current_step.id if current_step else None,
            actor_id=user.id,
            action=action,
            remarks=remarks,
            from_status=from_status.value if from_status else None,
            to_status=new_status.value if new_status else None,
        )
        self.session.add(wf_action)
        await self.session.flush()

        return ActionResult(
            instance=instance,
            action=wf_action,
            new_status=new_status,
            is_complete=instance.is_complete,
        )

    async def _advance(self, application, instance: WorkflowInstance, current_step) -> ApplicationStatus:
        """Move the instance to the next step or complete it."""
        if current_step is None:
            self._complete(instance)
            return ApplicationStatus.COMPLETED

        next_step = await self.steps.next_step(instance.workflow_id, current_step.step_order)
        if next_step is None or current_step.is_final:
            self._complete(instance)
            return ApplicationStatus.COMPLETED

        instance.current_step_id = next_step.id
        return ApplicationStatus.FORWARDED

    def _complete(self, instance: WorkflowInstance) -> None:
        instance.is_complete = True
        instance.completed_at = self._now()
        instance.current_step_id = None
