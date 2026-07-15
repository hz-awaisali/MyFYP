"""Dashboard response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel
from app.analytics.schemas import AnalyticsOverview


class DashboardActivity(BaseModel):
    application_id: uuid.UUID
    subject: str | None = None
    action: str
    status: str
    timestamp: datetime
    remarks: str | None = None


class StudentDashboardSummary(BaseModel):
    my_applications_count: dict[str, int]
    recent_activity: list[DashboardActivity]


class ApproverDashboardSummary(BaseModel):
    pending_my_approval_count: int
    recently_actioned: list[DashboardActivity]


class DashboardSummary(BaseModel):
    student_summary: StudentDashboardSummary | None = None
    approver_summary: ApproverDashboardSummary | None = None
    admin_summary: AnalyticsOverview | None = None
