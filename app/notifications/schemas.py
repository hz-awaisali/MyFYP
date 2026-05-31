"""Notification schemas."""

import uuid
from datetime import datetime

from app.common.enums import NotificationType
from app.common.schemas import ORMBase


class NotificationRead_(ORMBase):
    id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class UnreadCount(ORMBase):
    unread: int
