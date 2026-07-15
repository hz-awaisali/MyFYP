"""Audit log repository."""

import uuid

from sqlalchemy import func, select

from app.common.repository import BaseRepository
from app.audit_logs.models import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        term: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        conditions = []
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id:
            conditions.append(AuditLog.entity_id == entity_id)
        if actor_id:
            conditions.append(AuditLog.actor_id == actor_id)
        if term:
            like = f"%{term}%"
            conditions.append(
                AuditLog.action.ilike(like)
                | AuditLog.entity_type.ilike(like)
                | AuditLog.remarks.ilike(like)
            )

        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)
        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
