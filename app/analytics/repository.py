"""Repository for analytics queries."""

import uuid
from datetime import datetime
from sqlalchemy import select, func, case, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.models import Application, ApplicationCategory
from app.departments.models import Department
from app.workflows.models import WorkflowInstance, WorkflowDefinition, WorkflowAction
from app.common.enums import ApplicationStatus


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_overview(
        self,
        *,
        department_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        conditions = []
        if department_id is not None:
            conditions.append(Application.department_id == department_id)
        if start_date is not None:
            conditions.append(Application.created_at >= start_date)
        if end_date is not None:
            conditions.append(Application.created_at <= end_date)

        stmt = select(
            func.count(Application.id).label("total"),
            func.count(
                case(
                    (
                        Application.status.in_(
                            [ApplicationStatus.PENDING, ApplicationStatus.SUBMITTED]
                        ),
                        1,
                    )
                )
            ).label("pending"),
            func.count(
                case(
                    (
                        Application.status.in_(
                            [ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]
                        ),
                        1,
                    )
                )
            ).label("approved"),
            func.count(
                case((Application.status == ApplicationStatus.REJECTED, 1))
            ).label("rejected"),
            func.count(
                case(
                    (
                        Application.status.in_(
                            [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.FORWARDED]
                        ),
                        1,
                    )
                )
            ).label("in_progress"),
        )

        for cond in conditions:
            stmt = stmt.where(cond)

        result = (await self.session.execute(stmt)).one()
        return {
            "total": result.total,
            "pending": result.pending,
            "approved": result.approved,
            "rejected": result.rejected,
            "in_progress": result.in_progress,
        }

    async def get_by_department(
        self,
        *,
        department_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        conditions = []
        if department_id is not None:
            conditions.append(Application.department_id == department_id)
        if start_date is not None:
            conditions.append(Application.created_at >= start_date)
        if end_date is not None:
            conditions.append(Application.created_at <= end_date)

        # Build query grouped by department and category
        stmt = (
            select(
                Application.department_id,
                Department.name.label("department_name"),
                Application.category_id,
                ApplicationCategory.name.label("category_name"),
                func.count(Application.id).label("total"),
                func.count(
                    case(
                        (
                            Application.status.in_(
                                [ApplicationStatus.PENDING, ApplicationStatus.SUBMITTED]
                            ),
                            1,
                        )
                    )
                ).label("pending"),
                func.count(
                    case(
                        (
                            Application.status.in_(
                                [ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]
                            ),
                            1,
                        )
                    )
                ).label("approved"),
                func.count(
                    case((Application.status == ApplicationStatus.REJECTED, 1))
                ).label("rejected"),
                func.count(
                    case(
                        (
                            Application.status.in_(
                                [
                                    ApplicationStatus.UNDER_REVIEW,
                                    ApplicationStatus.FORWARDED,
                                ]
                            ),
                            1,
                        )
                    )
                ).label("in_progress"),
            )
            .outerjoin(Department, Application.department_id == Department.id)
            .join(ApplicationCategory, Application.category_id == ApplicationCategory.id)
        )

        for cond in conditions:
            stmt = stmt.where(cond)

        stmt = stmt.group_by(
            Application.department_id,
            Department.name,
            Application.category_id,
            ApplicationCategory.name,
        )

        # Count total distinct groupings
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())

        # Execute paginated query
        stmt = stmt.order_by(Department.name, ApplicationCategory.name).offset(offset).limit(limit)
        results = (await self.session.execute(stmt)).all()

        items = []
        for r in results:
            items.append(
                {
                    "department_id": r.department_id,
                    "department_name": r.department_name or "General/No Department",
                    "category_id": r.category_id,
                    "category_name": r.category_name,
                    "total": r.total,
                    "pending": r.pending,
                    "approved": r.approved,
                    "rejected": r.rejected,
                    "in_progress": r.in_progress,
                }
            )

        return items, total

    async def get_workflow_instances(
        self,
        *,
        department_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[WorkflowInstance]:
        conditions = []
        if department_id is not None:
            conditions.append(Application.department_id == department_id)
        if start_date is not None:
            conditions.append(WorkflowInstance.started_at >= start_date)
        if end_date is not None:
            conditions.append(WorkflowInstance.started_at <= end_date)

        stmt = (
            select(WorkflowInstance)
            .join(Application, WorkflowInstance.application_id == Application.id)
            .options(
                selectinload(WorkflowInstance.actions),
                selectinload(WorkflowInstance.workflow).selectinload(WorkflowDefinition.steps),
            )
        )

        for cond in conditions:
            stmt = stmt.where(cond)

        return list((await self.session.execute(stmt)).scalars().all())

    async def get_approval_rate(
        self,
        *,
        department_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        conditions = []
        if department_id is not None:
            conditions.append(Application.department_id == department_id)
        if start_date is not None:
            conditions.append(Application.created_at >= start_date)
        if end_date is not None:
            conditions.append(Application.created_at <= end_date)

        # Overall approval rate
        stmt_overall = select(
            func.count(
                case(
                    (
                        Application.status.in_(
                            [ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]
                        ),
                        1,
                    )
                )
            ).label("approved"),
            func.count(
                case((Application.status == ApplicationStatus.REJECTED, 1))
            ).label("rejected"),
        )
        for cond in conditions:
            stmt_overall = stmt_overall.where(cond)
        overall_res = (await self.session.execute(stmt_overall)).one()

        approved = overall_res.approved
        rejected = overall_res.rejected
        ratio = None
        if (approved + rejected) > 0:
            ratio = approved / (approved + rejected)

        overall = {"approved": approved, "rejected": rejected, "ratio": ratio}

        # By department approval rate
        stmt_dept = (
            select(
                Application.department_id,
                Department.name.label("department_name"),
                func.count(
                    case(
                        (
                            Application.status.in_(
                                [ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]
                            ),
                            1,
                        )
                    )
                ).label("approved"),
                func.count(
                    case((Application.status == ApplicationStatus.REJECTED, 1))
                ).label("rejected"),
            )
            .outerjoin(Department, Application.department_id == Department.id)
            .group_by(Application.department_id, Department.name)
        )
        for cond in conditions:
            stmt_dept = stmt_dept.where(cond)

        dept_results = (await self.session.execute(stmt_dept)).all()
        departments = []
        for r in dept_results:
            d_app = r.approved
            d_rej = r.rejected
            d_ratio = None
            if (d_app + d_rej) > 0:
                d_ratio = d_app / (d_app + d_rej)
            departments.append(
                {
                    "department_id": r.department_id,
                    "department_name": r.department_name or "General/No Department",
                    "approved": d_app,
                    "rejected": d_rej,
                    "ratio": d_ratio,
                }
            )

        return {"overall": overall, "departments": departments}
