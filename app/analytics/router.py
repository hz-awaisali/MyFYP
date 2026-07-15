"""Analytics router."""

from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permissions, CurrentUser
from app.common.schemas import Page
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.analytics.schemas import (
    AnalyticsOverview,
    DepartmentCategoryAnalytics,
    TurnaroundStepAnalytics,
    ApprovalRateAnalytics,
    BottleneckAnalytics,
)
from app.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    dependencies=[Depends(require_permissions("view_analytics"))],
)
async def get_overview(
    current_user: CurrentUser,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService(db).get_overview(
        current_user, start_date=start_date, end_date=end_date
    )


@router.get(
    "/by-department",
    response_model=Page[DepartmentCategoryAnalytics],
    dependencies=[Depends(require_permissions("view_analytics"))],
)
async def get_by_department(
    current_user: CurrentUser,
    pagination: PaginationParams = Depends(pagination_params),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await AnalyticsService(db).get_by_department(
        current_user,
        start_date=start_date,
        end_date=end_date,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.get(
    "/turnaround",
    response_model=list[TurnaroundStepAnalytics],
    dependencies=[Depends(require_permissions("view_analytics"))],
)
async def get_turnaround(
    current_user: CurrentUser,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService(db).get_turnaround(
        current_user, start_date=start_date, end_date=end_date
    )


@router.get(
    "/approval-rate",
    response_model=ApprovalRateAnalytics,
    dependencies=[Depends(require_permissions("view_analytics"))],
)
async def get_approval_rate(
    current_user: CurrentUser,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService(db).get_approval_rate(
        current_user, start_date=start_date, end_date=end_date
    )


@router.get(
    "/bottlenecks",
    response_model=list[BottleneckAnalytics],
    dependencies=[Depends(require_permissions("view_analytics"))],
)
async def get_bottlenecks(
    current_user: CurrentUser,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await AnalyticsService(db).get_bottlenecks(
        current_user, start_date=start_date, end_date=end_date
    )
