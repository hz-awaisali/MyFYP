"""Audit log schemas."""

import uuid
from datetime import datetime

from app.common.schemas import ORMBase


class AuditLogRead(ORMBase):
    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    old_status: str | None = None
    new_status: str | None = None
    remarks: str | None = None
    department_id: uuid.UUID | None = None
    ip_address: str | None = None
    created_at: datetime
