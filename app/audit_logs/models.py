"""Audit log model: records every meaningful state change."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.common.models import Base, TimestampMixin, UUIDMixin


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)

    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str | None] = mapped_column(String(50))
    remarks: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
