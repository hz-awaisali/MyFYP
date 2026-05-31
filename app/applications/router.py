"""Application submission and processing endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.applications.schemas import (
    ApplicationActionInput,
    ApplicationCreate,
    ApplicationRead,
)
from app.applications.service import ApplicationService
from app.common.enums import ApplicationStatus
from app.common.schemas import Page
from app.core.database import get_db
from app.core.deps import CurrentUser, get_client_ip
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.workflows.repository import WorkflowInstanceRepository
from app.workflows.schemas import WorkflowInstanceRead

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", response_model=Page[ApplicationRead])
async def list_applications(
    current_user: CurrentUser,
    pagination: PaginationParams = Depends(pagination_params),
    status: ApplicationStatus | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List applications scoped to the caller (own / department / all)."""
    items, total = await ApplicationService(db).list_for_user(
        current_user,
        offset=pagination.offset,
        limit=pagination.limit,
        status=status,
        category_id=category_id,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.post("", response_model=ApplicationRead, status_code=201)
async def create_application(
    data: ApplicationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a draft application with form responses."""
    return await ApplicationService(db).create_draft(data, current_user)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService(db).get_for_user(application_id, current_user)


@router.post("/{application_id}/submit", response_model=ApplicationRead)
async def submit_application(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService(db).submit(
        application_id, current_user, ip=get_client_ip(request)
    )


@router.post("/{application_id}/actions", response_model=ApplicationRead)
async def act_on_application(
    application_id: uuid.UUID,
    data: ApplicationActionInput,
    current_user: CurrentUser,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Approve / reject / forward / return / add remarks / close / reopen."""
    return await ApplicationService(db).act(
        application_id,
        current_user,
        data.action,
        data.remarks,
        ip=get_client_ip(request),
    )


@router.get("/{application_id}/timeline", response_model=WorkflowInstanceRead)
async def application_timeline(
    application_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return the workflow instance and its action history (audit timeline)."""
    # Access check via the application itself.
    await ApplicationService(db).get_for_user(application_id, current_user)
    instance = await WorkflowInstanceRepository(db).get_by_application(application_id)
    if instance is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("No workflow instance for this application")
    return instance
