"""Application category and form-builder endpoints (admin configuration)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.category_service import CategoryService
from app.applications.schemas import (
    CategoryCreate,
    CategoryDetail,
    CategoryRead,
    CategoryUpdate,
    FieldCreate,
    FieldRead,
    FormCreate,
    FormRead,
)
from app.common.schemas import Message, Page
from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.pagination import PaginationParams, build_page_meta, pagination_params

router = APIRouter(prefix="/application-categories", tags=["Application Categories & Forms"])


@router.get("", response_model=Page[CategoryRead])
async def list_categories(
    pagination: PaginationParams = Depends(pagination_params),
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    items, total = await CategoryService(db).list(
        offset=pagination.offset,
        limit=pagination.limit,
        enabled_only=enabled_only,
        term=pagination.search,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.post("", response_model=CategoryDetail, status_code=201)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    return await CategoryService(db).create(data)


@router.get("/{category_id}", response_model=CategoryDetail)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).get(category_id)


@router.patch("/{category_id}", response_model=CategoryDetail)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    return await CategoryService(db).update(category_id, data)


@router.delete("/{category_id}", response_model=Message)
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    await CategoryService(db).delete(category_id)
    return Message(message="Category deleted")


@router.post("/{category_id}/forms", response_model=FormRead, status_code=201)
async def create_form(
    category_id: uuid.UUID,
    data: FormCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    return await CategoryService(db).create_form(category_id, data)


@router.get("/forms/{form_id}", response_model=FormRead)
async def get_form(form_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).get_form(form_id)


@router.post("/forms/{form_id}/fields", response_model=FieldRead, status_code=201)
async def add_field(
    form_id: uuid.UUID,
    data: FieldCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    return await CategoryService(db).add_field(form_id, data)


@router.delete("/fields/{field_id}", response_model=Message)
async def delete_field(
    field_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("manage_application_categories")),
):
    await CategoryService(db).delete_field(field_id)
    return Message(message="Field deleted")
