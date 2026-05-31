"""Audit logging service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_logs.models import AuditLog
from app.audit_logs.repository import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        old_status: str | None = None,
        new_status: str | None = None,
        remarks: str | None = None,
        department_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
            department_id=department_id,
            ip_address=ip_address,
        )
        return await self.repo.add(log)

    async def search(self, **kwargs):
        return await self.repo.search(**kwargs)
