"""Application category and dynamic form-builder management service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.models import (
    ApplicationCategory,
    ApplicationField,
    ApplicationForm,
)
from app.applications.repository import (
    CategoryRepository,
    FieldRepository,
    FormRepository,
)
from app.applications.schemas import (
    CategoryCreate,
    CategoryUpdate,
    FieldCreate,
    FormCreate,
)
from app.core.exceptions import NotFoundError, ValidationError


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.categories = CategoryRepository(session)
        self.forms = FormRepository(session)
        self.fields = FieldRepository(session)

    async def get(self, category_id: uuid.UUID) -> ApplicationCategory:
        category = await self.categories.get_with_forms(category_id)
        if category is None:
            raise NotFoundError("Application category not found")
        return category

    async def list(self, *, offset, limit, enabled_only=False, term=None):
        return await self.categories.list_paginated(
            offset=offset, limit=limit, enabled_only=enabled_only, term=term
        )

    async def create(self, data: CategoryCreate) -> ApplicationCategory:
        category = ApplicationCategory(
            name=data.name,
            description=data.description,
            department_id=data.department_id,
            workflow_id=data.workflow_id,
        )
        await self.categories.add(category)
        await self.session.commit()
        return await self.categories.get_with_forms(category.id)

    async def update(self, category_id: uuid.UUID, data: CategoryUpdate) -> ApplicationCategory:
        category = await self.get(category_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        await self.session.commit()
        return await self.categories.get_with_forms(category.id)

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get(category_id)
        await self.categories.delete(category)
        await self.session.commit()

    # --- Forms / form builder ---
    def _build_field(self, form_id: uuid.UUID, data: FieldCreate) -> ApplicationField:
        from app.common.enums import FieldType

        if data.field_type in (FieldType.DROPDOWN, FieldType.RADIO, FieldType.CHECKBOX) and not data.options:
            raise ValidationError(f"Field '{data.key}' of type {data.field_type.value} requires options")
        return ApplicationField(
            form_id=form_id,
            key=data.key,
            label=data.label,
            field_type=data.field_type,
            is_required=data.is_required,
            default_value=data.default_value,
            validation=data.validation,
            options=data.options,
            display_order=data.display_order,
            visibility_rule=data.visibility_rule,
        )

    async def create_form(self, category_id: uuid.UUID, data: FormCreate) -> ApplicationForm:
        await self.get(category_id)
        keys = [f.key for f in data.fields]
        if len(keys) != len(set(keys)):
            raise ValidationError("Field keys must be unique within a form")

        form = ApplicationForm(category_id=category_id, name=data.name)
        await self.forms.add(form)
        for field in data.fields:
            self.session.add(self._build_field(form.id, field))
        await self.session.commit()
        return await self.forms.get_with_fields(form.id)

    async def get_form(self, form_id: uuid.UUID) -> ApplicationForm:
        form = await self.forms.get_with_fields(form_id)
        if form is None:
            raise NotFoundError("Form not found")
        return form

    async def add_field(self, form_id: uuid.UUID, data: FieldCreate) -> ApplicationField:
        form = await self.get_form(form_id)
        if any(f.key == data.key for f in form.fields):
            raise ValidationError(f"Field key '{data.key}' already exists on this form")
        field = self._build_field(form_id, data)
        await self.fields.add(field)
        await self.session.commit()
        return field

    async def delete_field(self, field_id: uuid.UUID) -> None:
        field = await self.fields.get(field_id)
        if field is None:
            raise NotFoundError("Field not found")
        await self.fields.delete(field)
        await self.session.commit()
