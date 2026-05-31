"""Department and Program models."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.common.models import Base, TimestampMixin, UUIDMixin


class Department(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # use_alter breaks the circular users <-> departments FK dependency so the
    # FK is added via ALTER TABLE after both tables exist (required on Postgres).
    hod_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_departments_hod_id_users"),
        index=True,
    )

    hod: Mapped["User | None"] = relationship(foreign_keys=[hod_id])  # noqa: F821
    members: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="department",
        primaryjoin="Department.id == User.department_id",
        foreign_keys="User.department_id",
    )
    programs: Mapped[list["Program"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )


class Program(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "programs"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    duration_years: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    department_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    department: Mapped[Department] = relationship(back_populates="programs")
    students: Mapped[list["StudentProfile"]] = relationship(back_populates="program")  # noqa: F821
