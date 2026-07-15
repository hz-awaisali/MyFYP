"""Application domain models: categories, dynamic forms, fields, applications, responses."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.users.models import User

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.common.enums import ApplicationStatus, FieldType
from app.common.models import Base, TimestampMixin, UUIDMixin


class ApplicationCategory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_categories"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("workflow_definitions.id", ondelete="SET NULL"), index=True
    )

    forms: Mapped[list["ApplicationForm"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class ApplicationForm(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_forms"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("application_categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[ApplicationCategory] = relationship(back_populates="forms")
    fields: Mapped[list["ApplicationField"]] = relationship(
        back_populates="form",
        cascade="all, delete-orphan",
        order_by="ApplicationField.display_order",
    )


class ApplicationField(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_fields"

    form_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("application_forms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Machine key used in responses (e.g. "reason"); label is the display text.
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[FieldType] = mapped_column(
        SAEnum(FieldType, name="field_type"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text)
    # Validation rules, e.g. {"min": 1, "max": 100, "pattern": "..."}
    validation: Mapped[dict | None] = mapped_column(JSON)
    # Options for dropdown/radio/checkbox: ["A", "B"]
    options: Mapped[list | None] = mapped_column(JSON)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Architecture placeholder for conditional visibility rules.
    visibility_rule: Mapped[dict | None] = mapped_column(JSON)

    form: Mapped[ApplicationForm] = relationship(back_populates="fields")


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("application_categories.id"), index=True, nullable=False
    )
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("application_forms.id", ondelete="SET NULL")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Denormalized owning department for scoping (from the category).
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(255))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[ApplicationCategory] = relationship()
    responses: Mapped[list["ApplicationResponse"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    student: Mapped["User"] = relationship(foreign_keys=[student_id])


class ApplicationResponse(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_responses"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("application_fields.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)

    application: Mapped[Application] = relationship(back_populates="responses")
