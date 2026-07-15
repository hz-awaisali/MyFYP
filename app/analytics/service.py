"""Analytics service."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repository import AnalyticsRepository
from app.core.exceptions import PermissionDeniedError
from app.users.models import User
from app.roles.models import Role
from app.common.enums import WorkflowActionType


def _make_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AnalyticsRepository(session)

    def _get_department_scope(self, user: User) -> uuid.UUID | None:
        if user.is_super_admin or "view_all_applications" in user.permissions:
            return None
        if "view_department_applications" in user.permissions:
            if user.department_id is None:
                raise PermissionDeniedError("User has department scope but no department assigned")
            return user.department_id
        raise PermissionDeniedError("You do not have permission to view analytics")

    async def get_overview(
        self,
        user: User,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        dept_id = self._get_department_scope(user)
        return await self.repo.get_overview(
            department_id=dept_id, start_date=start_date, end_date=end_date
        )

    async def get_by_department(
        self,
        user: User,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        dept_id = self._get_department_scope(user)
        return await self.repo.get_by_department(
            department_id=dept_id,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

    async def get_turnaround(
        self,
        user: User,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        dept_id = self._get_department_scope(user)
        instances = await self.repo.get_workflow_instances(
            department_id=dept_id, start_date=start_date, end_date=end_date
        )

        # Get role map for role names
        roles_stmt = select(Role)
        roles = (await self.session.execute(roles_stmt)).scalars().all()
        role_map = {r.id: r.name for r in roles}

        step_durations = {}  # step_id -> list of floats (seconds)
        step_info = {}       # step_id -> WorkflowStep

        for inst in instances:
            if not inst.workflow or not inst.workflow.steps:
                continue
            steps = inst.workflow.steps
            steps_by_id = {s.id: s for s in steps}

            current_step = steps[0]
            entry_time = _make_aware(inst.started_at)

            # Sort actions by creation time
            actions = sorted(inst.actions, key=lambda a: _make_aware(a.created_at) or datetime.min)

            for act in actions:
                act_created_at = _make_aware(act.created_at)
                if act.step_id == current_step.id:
                    if act.action in (
                        WorkflowActionType.APPROVE,
                        WorkflowActionType.FORWARD,
                        WorkflowActionType.REJECT,
                        WorkflowActionType.CLOSE,
                        WorkflowActionType.RETURN_FOR_CORRECTION,
                    ):
                        duration = (act_created_at - entry_time).total_seconds()
                        if duration >= 0:
                            step_durations.setdefault(current_step.id, []).append(duration)
                            step_info[current_step.id] = current_step

                        if act.action in (WorkflowActionType.APPROVE, WorkflowActionType.FORWARD):
                            # Move to next step by step_order
                            next_step = None
                            for s in steps:
                                if s.step_order > current_step.step_order:
                                    next_step = s
                                    break
                            if next_step and not current_step.is_final:
                                current_step = next_step
                                entry_time = act_created_at
                            else:
                                current_step = None
                        else:
                            current_step = None
                    elif act.action == WorkflowActionType.REOPEN:
                        current_step = steps[0]
                        entry_time = act_created_at

        turnaround_list = []
        for step_id, durations in step_durations.items():
            step = step_info[step_id]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            turnaround_list.append(
                {
                    "step_id": step_id,
                    "step_name": step.name,
                    "role_id": step.role_id,
                    "role_name": role_map.get(step.role_id) if step.role_id else None,
                    "avg_duration_seconds": avg_duration,
                    "count": len(durations),
                }
            )

        return turnaround_list

    async def get_bottlenecks(
        self,
        user: User,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        dept_id = self._get_department_scope(user)
        instances = await self.repo.get_workflow_instances(
            department_id=dept_id, start_date=start_date, end_date=end_date
        )

        roles_stmt = select(Role)
        roles = (await self.session.execute(roles_stmt)).scalars().all()
        role_map = {r.id: r.name for r in roles}

        step_pending_durations = {}  # step_id -> list of floats (seconds)
        step_info = {}               # step_id -> WorkflowStep
        now = datetime.now(timezone.utc)

        for inst in instances:
            if not inst.workflow or not inst.workflow.steps:
                continue
            steps = inst.workflow.steps
            current_step = steps[0]
            entry_time = _make_aware(inst.started_at)

            # Sort actions by creation time
            actions = sorted(inst.actions, key=lambda a: _make_aware(a.created_at) or datetime.min)

            for act in actions:
                act_created_at = _make_aware(act.created_at)
                if act.step_id == current_step.id:
                    if act.action in (
                        WorkflowActionType.APPROVE,
                        WorkflowActionType.FORWARD,
                        WorkflowActionType.REJECT,
                        WorkflowActionType.CLOSE,
                        WorkflowActionType.RETURN_FOR_CORRECTION,
                    ):
                        duration = (act_created_at - entry_time).total_seconds()
                        if duration >= 0:
                            step_pending_durations.setdefault(current_step.id, []).append(duration)
                            step_info[current_step.id] = current_step

                        if act.action in (WorkflowActionType.APPROVE, WorkflowActionType.FORWARD):
                            next_step = None
                            for s in steps:
                                if s.step_order > current_step.step_order:
                                    next_step = s
                                    break
                            if next_step and not current_step.is_final:
                                current_step = next_step
                                entry_time = act_created_at
                            else:
                                current_step = None
                        else:
                            current_step = None
                    elif act.action == WorkflowActionType.REOPEN:
                        current_step = steps[0]
                        entry_time = act_created_at

            # If the instance is not complete and is currently stuck at a step, include the pending duration
            if not inst.is_complete and current_step is not None:
                duration = (now - entry_time).total_seconds()
                if duration >= 0:
                    step_pending_durations.setdefault(current_step.id, []).append(duration)
                    step_info[current_step.id] = current_step

        bottleneck_list = []
        for step_id, durations in step_pending_durations.items():
            step = step_info[step_id]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            bottleneck_list.append(
                {
                    "step_id": step_id,
                    "step_name": step.name,
                    "role_id": step.role_id,
                    "role_name": role_map.get(step.role_id) if step.role_id else None,
                    "avg_pending_duration_seconds": avg_duration,
                    "count": len(durations),
                }
            )

        # Sort descending by average pending duration
        bottleneck_list = sorted(
            bottleneck_list, key=lambda x: x["avg_pending_duration_seconds"], reverse=True
        )
        return bottleneck_list

    async def get_approval_rate(
        self,
        user: User,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        dept_id = self._get_department_scope(user)
        return await self.repo.get_approval_rate(
            department_id=dept_id, start_date=start_date, end_date=end_date
        )
