"""Workflow engine models: definitions, steps, instances and actions.

Workflows are pure data. The engine interprets these rows at runtime so any
approval chain can be configured without code changes.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.users.models import User

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.common.enums import WorkflowActionType
from app.common.models import Base, TimestampMixin, UUIDMixin


class WorkflowDefinition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_definitions"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )


class WorkflowStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_definitions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # The role expected to act at this step.
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="SET NULL"), index=True
    )
    # Optional fixed department; if null, the engine uses the application's department.
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )

    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_forward: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_return: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_reject: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workflow: Mapped[WorkflowDefinition] = relationship(back_populates="steps")


class WorkflowInstance(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_instances"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_definitions.id"), index=True, nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_steps.id", ondelete="SET NULL")
    )
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow: Mapped[WorkflowDefinition] = relationship()
    current_step: Mapped[WorkflowStep | None] = relationship()
    actions: Mapped[list["WorkflowAction"]] = relationship(
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="WorkflowAction.created_at",
    )


class WorkflowAction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_actions"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workflow_instances.id", ondelete="CASCADE"), index=True, nullable=False
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_steps.id", ondelete="SET NULL")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[WorkflowActionType] = mapped_column(
        SAEnum(WorkflowActionType, name="workflow_action_type"), nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(Text)
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str | None] = mapped_column(String(50))

    instance: Mapped[WorkflowInstance] = relationship(back_populates="actions")
    actor: Mapped["User | None"] = relationship(lazy="selectin")
    step: Mapped["WorkflowStep | None"] = relationship(lazy="selectin")
