"""Audit log endpoints (read-only)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_logs.schemas import AuditLogRead
from app.audit_logs.service import AuditService
from app.common.schemas import Page
from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.pagination import PaginationParams, build_page_meta, pagination_params

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=Page[AuditLogRead])
async def list_audit_logs(
    pagination: PaginationParams = Depends(pagination_params),
    entity_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    actor_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("view_all_applications")),
):
    items, total = await AuditService(db).search(
        offset=pagination.offset,
        limit=pagination.limit,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        term=pagination.search,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))
