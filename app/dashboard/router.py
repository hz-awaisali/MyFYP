"""Dashboard router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.dashboard.schemas import DashboardSummary
from app.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a dashboard summary customized for the caller's role."""
    return await DashboardService(db).get_summary(current_user)
