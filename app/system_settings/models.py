"""System settings key/value model for configurable runtime rules."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, TimestampMixin, UUIDMixin


class SystemSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
