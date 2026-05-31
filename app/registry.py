"""Imports every ORM model so that ``Base.metadata`` is fully populated.

Used by Alembic (autogenerate) and by the test harness that creates tables.
Import this module for its side effects.
"""

from app.common.models import Base  # noqa: F401

# Core domain models
from app.roles.models import Permission, Role, role_permissions  # noqa: F401
from app.users.models import StudentProfile, User  # noqa: F401
from app.departments.models import Department, Program  # noqa: F401
from app.applications.models import (  # noqa: F401
    Application,
    ApplicationCategory,
    ApplicationField,
    ApplicationForm,
    ApplicationResponse,
)
from app.workflows.models import (  # noqa: F401
    WorkflowAction,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStep,
)
from app.notifications.models import Notification, NotificationRead  # noqa: F401
from app.attachments.models import Attachment  # noqa: F401
from app.audit_logs.models import AuditLog  # noqa: F401
from app.system_settings.models import SystemSetting  # noqa: F401

__all__ = ["Base"]
