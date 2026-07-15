"""Schemas for the analytics module."""

import uuid
from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    in_progress: int


class DepartmentCategoryAnalytics(BaseModel):
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    category_id: uuid.UUID
    category_name: str
    total: int
    pending: int
    approved: int
    rejected: int
    in_progress: int


class TurnaroundStepAnalytics(BaseModel):
    step_id: uuid.UUID
    step_name: str
    role_id: uuid.UUID | None = None
    role_name: str | None = None
    avg_duration_seconds: float
    count: int


class ApprovalRateDetail(BaseModel):
    approved: int
    rejected: int
    ratio: float | None = None


class DepartmentApprovalRate(BaseModel):
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    approved: int
    rejected: int
    ratio: float | None = None


class ApprovalRateAnalytics(BaseModel):
    overall: ApprovalRateDetail
    departments: list[DepartmentApprovalRate]


class BottleneckAnalytics(BaseModel):
    step_id: uuid.UUID
    step_name: str
    role_id: uuid.UUID | None = None
    role_name: str | None = None
    avg_pending_duration_seconds: float
    count: int
