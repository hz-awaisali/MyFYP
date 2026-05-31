"""Application module repositories."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.applications.models import (
    Application,
    ApplicationCategory,
    ApplicationField,
    ApplicationForm,
)
from app.common.enums import ApplicationStatus
from app.common.repository import BaseRepository


class CategoryRepository(BaseRepository[ApplicationCategory]):
    model = ApplicationCategory

    async def get_with_forms(self, id_) -> ApplicationCategory | None:
        stmt = (
            select(ApplicationCategory)
            .where(ApplicationCategory.id == id_)
            .options(
                selectinload(ApplicationCategory.forms).selectinload(ApplicationForm.fields)
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(self, *, offset, limit, enabled_only=False, term=None):
        stmt = select(ApplicationCategory)
        count_stmt = select(func.count()).select_from(ApplicationCategory)
        if enabled_only:
            stmt = stmt.where(ApplicationCategory.is_enabled.is_(True))
            count_stmt = count_stmt.where(ApplicationCategory.is_enabled.is_(True))
        if term:
            like = f"%{term}%"
            stmt = stmt.where(ApplicationCategory.name.ilike(like))
            count_stmt = count_stmt.where(ApplicationCategory.name.ilike(like))
        stmt = stmt.order_by(ApplicationCategory.name).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total


class FormRepository(BaseRepository[ApplicationForm]):
    model = ApplicationForm

    async def get_with_fields(self, id_) -> ApplicationForm | None:
        stmt = (
            select(ApplicationForm)
            .where(ApplicationForm.id == id_)
            .options(selectinload(ApplicationForm.fields))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def active_form_for_category(self, category_id: uuid.UUID) -> ApplicationForm | None:
        stmt = (
            select(ApplicationForm)
            .where(
                ApplicationForm.category_id == category_id,
                ApplicationForm.is_active.is_(True),
            )
            .options(selectinload(ApplicationForm.fields))
            .order_by(ApplicationForm.version.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class FieldRepository(BaseRepository[ApplicationField]):
    model = ApplicationField


class ApplicationRepository(BaseRepository[Application]):
    model = Application

    async def get_full(self, id_) -> Application | None:
        stmt = (
            select(Application)
            .where(Application.id == id_)
            .options(selectinload(Application.responses))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        student_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        status: ApplicationStatus | None = None,
    ) -> tuple[list[Application], int]:
        conditions = []
        if student_id is not None:
            conditions.append(Application.student_id == student_id)
        if department_id is not None:
            conditions.append(Application.department_id == department_id)
        if category_id is not None:
            conditions.append(Application.category_id == category_id)
        if status is not None:
            conditions.append(Application.status == status)

        stmt = select(Application).options(selectinload(Application.responses))
        count_stmt = select(func.count()).select_from(Application)
        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Application.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
