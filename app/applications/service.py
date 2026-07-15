"""Application lifecycle service: draft, submit, act, list (with scoping)."""

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.applications.models import Application, ApplicationResponse
from app.applications.repository import (
    ApplicationRepository,
    CategoryRepository,
    FormRepository,
)
from app.applications.schemas import ApplicationCreate
from app.applications.validation import validate_responses
from app.audit_logs.service import AuditService
from app.common.enums import (
    ApplicationStatus,
    NotificationType,
    WorkflowActionType,
)
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.notifications.service import NotificationService
from app.users.models import User
from app.workflows.engine import WorkflowEngine
from app.workflows.repository import WorkflowInstanceRepository, WorkflowStepRepository
from app.workflows.models import WorkflowInstance, WorkflowStep
from app.ai_services.provider import get_ai_provider
import json

# Map workflow actions to the notification type sent to the student.
_ACTION_NOTIFICATIONS = {
    WorkflowActionType.APPROVE: NotificationType.APPLICATION_APPROVED,
    WorkflowActionType.FORWARD: NotificationType.APPLICATION_FORWARDED,
    WorkflowActionType.REJECT: NotificationType.APPLICATION_REJECTED,
    WorkflowActionType.RETURN_FOR_CORRECTION: NotificationType.APPLICATION_RETURNED,
    WorkflowActionType.ADD_REMARKS: NotificationType.NEW_REMARK,
}


class ApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ApplicationRepository(session)
        self.categories = CategoryRepository(session)
        self.forms = FormRepository(session)
        self.engine = WorkflowEngine(session)
        self.instances = WorkflowInstanceRepository(session)
        self.steps = WorkflowStepRepository(session)
        self.notifications = NotificationService(session)
        self.audit = AuditService(session)

    async def get_for_user(self, application_id: uuid.UUID, user: User) -> Application:
        application = await self.repo.get_full(application_id)
        if application is None:
            raise NotFoundError("Application not found")
        self._ensure_can_view(application, user)
        return application

    def _ensure_can_view(self, application: Application, user: User) -> None:
        if user.is_super_admin or "view_all_applications" in user.permissions:
            return
        if application.student_id == user.id:
            return
        if (
            "view_department_applications" in user.permissions
            and application.department_id is not None
            and application.department_id == user.department_id
        ):
            return
        raise PermissionDeniedError("You cannot access this application")

    async def list_for_user(
        self, user: User, *, offset, limit, status=None, category_id=None, term=None
    ) -> tuple[list[Application], int]:
        student_id = None
        department_id = None
        if user.is_super_admin or "view_all_applications" in user.permissions:
            pass
        elif "view_department_applications" in user.permissions:
            department_id = user.department_id
        else:
            student_id = user.id
        return await self.repo.search(
            offset=offset,
            limit=limit,
            student_id=student_id,
            department_id=department_id,
            category_id=category_id,
            status=status,
            term=term,
        )

    async def create_draft(self, data: ApplicationCreate, user: User) -> Application:
        category = await self.categories.get(data.category_id)
        if category is None:
            raise NotFoundError("Application category not found")
        if not category.is_enabled:
            raise ValidationError("This application category is currently disabled")

        form = await self.forms.active_form_for_category(category.id)
        responses_map = {r.field_key: r.value for r in data.responses}
        normalized = validate_responses(form.fields if form else [], responses_map)

        application = Application(
            category_id=category.id,
            form_id=form.id if form else None,
            student_id=user.id,
            department_id=category.department_id,
            status=ApplicationStatus.DRAFT,
            subject=data.subject,
        )
        await self.repo.add(application)

        if form:
            field_by_key = {f.key: f for f in form.fields}
            for key, value in normalized.items():
                application_response = ApplicationResponse(
                    application_id=application.id,
                    field_id=field_by_key[key].id,
                    field_key=key,
                    value=value,
                )
                self.session.add(application_response)

        await self.audit.record(
            action="create",
            entity_type="application",
            entity_id=application.id,
            actor_id=user.id,
            actor_role=user.role.name if user.role else None,
            new_status=ApplicationStatus.DRAFT.value,
            department_id=application.department_id,
        )
        await self.session.commit()
        return await self.repo.get_full(application.id)

    async def submit(self, application_id: uuid.UUID, user: User, *, ip: str | None = None) -> Application:
        application = await self.repo.get_full(application_id)
        if application is None:
            raise NotFoundError("Application not found")
        if application.student_id != user.id and not user.is_super_admin:
            raise PermissionDeniedError("Only the owner can submit this application")
        if application.status not in (ApplicationStatus.DRAFT, ApplicationStatus.RETURNED):
            raise ValidationError(f"Cannot submit an application in '{application.status.value}' status")

        category = await self.categories.get(application.category_id)
        previous = application.status

        instance = await self.instances.get_by_application(application.id)
        if category.workflow_id:
            if instance is None:
                instance = await self.engine.start(
                    application_id=application.id, workflow_id=category.workflow_id
                )
            application.status = ApplicationStatus.PENDING
        else:
            # No workflow configured -> goes straight to submitted/pending.
            application.status = ApplicationStatus.SUBMITTED

        application.submitted_at = datetime.now(timezone.utc)

        await self.audit.record(
            action="submit",
            entity_type="application",
            entity_id=application.id,
            actor_id=user.id,
            actor_role=user.role.name if user.role else None,
            old_status=previous.value,
            new_status=application.status.value,
            department_id=application.department_id,
            ip_address=ip,
        )
        # Confirmation to the student.
        await self.notifications.notify(
            user_id=application.student_id,
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            title="Application submitted",
            body=f"Your application '{application.subject or category.name}' has been submitted.",
            reference_type="application",
            reference_id=application.id,
            department_id=application.department_id,
        )
        # Notify assignees of the current step.
        if instance and instance.current_step_id:
            await self._notify_step_assignees(application, instance.current_step_id, category.name)

        await self.session.commit()
        return await self.repo.get_full(application.id)

    async def act(
        self,
        application_id: uuid.UUID,
        user: User,
        action: WorkflowActionType,
        remarks: str | None,
        *,
        ip: str | None = None,
    ) -> Application:
        application = await self.repo.get_full(application_id)
        if application is None:
            raise NotFoundError("Application not found")

        instance = await self.instances.get_by_application(application.id)
        if instance is None:
            raise ValidationError("This application has no active workflow")

        if not user.is_super_admin and "approve_application" not in user.permissions:
            raise PermissionDeniedError("You do not have permission to act on applications")

        previous = application.status
        result = await self.engine.act(
            application=application,
            instance=instance,
            user=user,
            action=action,
            remarks=remarks,
        )

        await self.audit.record(
            action=action.value,
            entity_type="application",
            entity_id=application.id,
            actor_id=user.id,
            actor_role=user.role.name if user.role else None,
            old_status=previous.value,
            new_status=result.new_status.value,
            remarks=remarks,
            department_id=application.department_id,
            ip_address=ip,
        )

        notif_type = _ACTION_NOTIFICATIONS.get(action)
        if notif_type:
            await self.notifications.notify(
                user_id=application.student_id,
                notification_type=notif_type,
                title=f"Application {result.new_status.value}",
                body=remarks or f"Your application was updated: {action.value}.",
                reference_type="application",
                reference_id=application.id,
                department_id=application.department_id,
            )

        # On forward, notify the next step's assignees.
        if action in (WorkflowActionType.APPROVE, WorkflowActionType.FORWARD) and instance.current_step_id:
            category = await self.categories.get(application.category_id)
            await self._notify_step_assignees(
                application, instance.current_step_id, category.name if category else "application"
            )

        await self.session.commit()
        return await self.repo.get_full(application.id)

    async def _notify_step_assignees(
        self, application: Application, step_id: uuid.UUID, category_name: str
    ) -> None:
        step = await self.steps.get(step_id)
        if step is None or step.role_id is None:
            return
        target_department = step.department_id or application.department_id

        stmt = select(User).where(User.role_id == step.role_id)
        if target_department is not None:
            stmt = stmt.where(User.department_id == target_department)
        assignees = list((await self.session.execute(stmt)).scalars().all())

        for assignee in assignees:
            await self.notifications.notify(
                user_id=assignee.id,
                notification_type=NotificationType.APPLICATION_FORWARDED,
                title="Application awaiting your action",
                body=f"An application '{application.subject or category_name}' needs your review.",
                reference_type="application",
                reference_id=application.id,
                department_id=application.department_id,
            )

    async def generate_ai_draft(
        self,
        *,
        prompt: str,
        form_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        user: User,
    ) -> Application:
        # 1. Retrieve the target form
        if form_id:
            form = await self.forms.get_with_fields(form_id)
            if not form:
                raise NotFoundError("Form not found")
            category = await self.categories.get(form.category_id)
        elif category_id:
            category = await self.categories.get(category_id)
            if not category:
                raise NotFoundError("Category not found")
            form = await self.forms.active_form_for_category(category.id)
        else:
            raise ValidationError("Either form_id or category_id must be provided")

        if not category:
            raise NotFoundError("Application category or form not found")

        if not category.is_enabled:
            raise ValidationError("This application category is currently disabled")

        # 2. Build fields context for LLM
        fields_context = []
        if form:
            for field in form.fields:
                fields_context.append({
                    "key": field.key,
                    "label": field.label,
                    "type": field.field_type.value,
                    "options": field.options,
                })

        # 3. Call AI provider
        provider = get_ai_provider()
        generated = await provider.generate_application(
            prompt,
            context={"fields": fields_context}
        )

        # 4. Parse responses from structured_description and validate them
        try:
            responses_map = json.loads(generated.structured_description)
        except Exception:
            responses_map = {}

        # Run server-side validation
        normalized = validate_responses(form.fields if form else [], responses_map)

        # 5. Create application and responses in DRAFT state
        application = Application(
            category_id=category.id,
            form_id=form.id if form else None,
            student_id=user.id,
            department_id=category.department_id,
            status=ApplicationStatus.DRAFT,
            subject=generated.subject,
        )
        await self.repo.add(application)
        await self.session.flush()

        if form:
            field_by_key = {f.key: f for f in form.fields}
            for key, value in normalized.items():
                app_resp = ApplicationResponse(
                    application_id=application.id,
                    field_id=field_by_key[key].id,
                    field_key=key,
                    value=value,
                )
                self.session.add(app_resp)

        await self.audit.record(
            action="create_ai_draft",
            entity_type="application",
            entity_id=application.id,
            actor_id=user.id,
            actor_role=user.role.name if user.role else None,
            new_status=ApplicationStatus.DRAFT.value,
            department_id=application.department_id,
        )
        await self.session.commit()
        return await self.repo.get_full(application.id)

    async def check_slas_and_notify_assignees(self) -> dict:
        """Scan incomplete workflow instances and notify assignees if pending beyond SLA."""
        from app.system_settings.service import SystemSettingService
        settings_service = SystemSettingService(self.session)
        setting = await settings_service.get("sla_threshold_hours")
        threshold_hours = 48
        if setting and setting.value:
            try:
                threshold_hours = int(setting.value)
            except ValueError:
                pass

        stmt = (
            select(WorkflowInstance)
            .where(WorkflowInstance.is_complete.is_(False))
            .options(
                selectinload(WorkflowInstance.actions),
                selectinload(WorkflowInstance.current_step),
            )
        )
        instances = list((await self.session.execute(stmt)).scalars().all())

        now = datetime.now(timezone.utc)
        reminders_sent = 0

        for inst in instances:
            if not inst.current_step_id or not inst.current_step:
                continue

            actions = sorted(inst.actions, key=lambda a: a.created_at)
            step_pending_since = inst.started_at
            if actions:
                step_pending_since = actions[-1].created_at

            # Ensure timezone awareness
            if step_pending_since.tzinfo is None:
                step_pending_since = step_pending_since.replace(tzinfo=timezone.utc)

            pending_duration = (now - step_pending_since).total_seconds()
            pending_hours = pending_duration / 3600.0

            if pending_hours > threshold_hours:
                application = await self.repo.get_full(inst.application_id)
                if not application:
                    continue

                category = await self.categories.get(application.category_id)
                category_name = category.name if category else "application"

                target_department = inst.current_step.department_id or application.department_id

                stmt_users = select(User).where(User.role_id == inst.current_step.role_id)
                if target_department is not None:
                    stmt_users = stmt_users.where(User.department_id == target_department)
                assignees = list((await self.session.execute(stmt_users)).scalars().all())

                for assignee in assignees:
                    # Check duplicate reminder in last 24 hours
                    from app.notifications.models import Notification
                    check_time = now - timedelta(hours=24)
                    stmt_dup = select(func.count(Notification.id)).where(
                        Notification.user_id == assignee.id,
                        Notification.reference_id == application.id,
                        Notification.title.like("SLA Reminder:%"),
                        Notification.created_at >= check_time
                    )
                    dup_count = int((await self.session.execute(stmt_dup)).scalar_one())

                    if dup_count == 0:
                        await self.notifications.notify(
                            user_id=assignee.id,
                            notification_type=NotificationType.APPLICATION_FORWARDED,
                            title=f"SLA Reminder: Application Pending on {inst.current_step.name}",
                            body=(
                                f"The application '{application.subject or category_name}' "
                                f"has been pending your action on step '{inst.current_step.name}' "
                                f"for {int(pending_hours)} hours (SLA: {threshold_hours} hours)."
                            ),
                            reference_type="application",
                            reference_id=application.id,
                            department_id=application.department_id,
                        )
                        reminders_sent += 1

        await self.session.commit()
        return {"reminders_sent": reminders_sent, "threshold_hours": threshold_hours}

