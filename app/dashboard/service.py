"""Dashboard service."""

import uuid
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.applications.models import Application
from app.audit_logs.models import AuditLog
from app.workflows.models import WorkflowInstance, WorkflowStep, WorkflowAction
from app.workflows.engine import WorkflowEngine
from app.users.models import User
from app.dashboard.schemas import (
    DashboardSummary,
    StudentDashboardSummary,
    ApproverDashboardSummary,
    DashboardActivity,
)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.analytics = AnalyticsService(session)
        self.engine = WorkflowEngine(session)

    async def get_summary(self, user: User) -> DashboardSummary:
        # Admin Role: full system overview
        if user.is_super_admin or "view_all_applications" in user.permissions:
            overview = await self.analytics.get_overview(user)
            from app.analytics.schemas import AnalyticsOverview
            return DashboardSummary(
                admin_summary=AnalyticsOverview(**overview)
            )

        # Student Role
        if user.role.name == "student":
            # Counts by status
            stmt_counts = (
                select(Application.status, func.count(Application.id))
                .where(Application.student_id == user.id)
                .group_by(Application.status)
            )
            res = (await self.session.execute(stmt_counts)).all()
            my_counts = {status.value: count for status, count in res}

            # Recent activity
            stmt_logs = (
                select(AuditLog, Application)
                .join(Application, AuditLog.entity_id == Application.id)
                .where(Application.student_id == user.id)
                .order_by(AuditLog.created_at.desc())
                .limit(5)
            )
            logs_res = (await self.session.execute(stmt_logs)).all()
            recent_activity = []
            for log, app in logs_res:
                recent_activity.append(
                    DashboardActivity(
                        application_id=app.id,
                        subject=app.subject,
                        action=log.action,
                        status=log.new_status or app.status.value,
                        timestamp=log.created_at,
                        remarks=log.remarks,
                    )
                )

            return DashboardSummary(
                student_summary=StudentDashboardSummary(
                    my_applications_count=my_counts,
                    recent_activity=recent_activity,
                )
            )

        # Approver / Department Role
        if "approve_application" in user.permissions:
            # Pending my approval count
            stmt_instances = (
                select(WorkflowInstance, Application)
                .join(Application, WorkflowInstance.application_id == Application.id)
                .where(WorkflowInstance.is_complete.is_(False))
                .options(selectinload(WorkflowInstance.current_step))
            )
            instances_res = (await self.session.execute(stmt_instances)).all()
            pending_count = 0
            for inst, app in instances_res:
                if inst.current_step and self.engine.can_act(
                    user, inst.current_step, application_department_id=app.department_id
                ):
                    pending_count += 1

            # Recently actioned items
            stmt_actions = (
                select(WorkflowAction, Application)
                .join(WorkflowInstance, WorkflowAction.instance_id == WorkflowInstance.id)
                .join(Application, WorkflowInstance.application_id == Application.id)
                .where(WorkflowAction.actor_id == user.id)
                .order_by(WorkflowAction.created_at.desc())
                .limit(5)
            )
            actions_res = (await self.session.execute(stmt_actions)).all()
            recently_actioned = []
            for act, app in actions_res:
                recently_actioned.append(
                    DashboardActivity(
                        application_id=app.id,
                        subject=app.subject,
                        action=act.action.value,
                        status=act.to_status or app.status.value,
                        timestamp=act.created_at,
                        remarks=act.remarks,
                    )
                )

            return DashboardSummary(
                approver_summary=ApproverDashboardSummary(
                    pending_my_approval_count=pending_count,
                    recently_actioned=recently_actioned,
                )
            )

        # Fallback empty summary
        return DashboardSummary()
