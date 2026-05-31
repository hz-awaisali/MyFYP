"""User and StudentProfile models."""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.common.enums import UserStatus
from app.common.models import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status"),
        default=UserStatus.PENDING,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roles.id"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )

    role: Mapped["Role"] = relationship(back_populates="users", lazy="selectin")  # noqa: F821
    department: Mapped["Department | None"] = relationship(  # noqa: F821
        back_populates="members", foreign_keys=[department_id]
    )
    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def permissions(self) -> set[str]:
        return self.role.permission_codes if self.role else set()

    @property
    def is_super_admin(self) -> bool:
        return bool(self.role and self.role.name == "super_admin")


class StudentProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    registration_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("programs.id", ondelete="SET NULL"), index=True
    )
    semester: Mapped[int | None] = mapped_column()
    batch: Mapped[str | None] = mapped_column(String(20))

    user: Mapped[User] = relationship(back_populates="student_profile")
    program: Mapped["Program | None"] = relationship(back_populates="students")  # noqa: F821
