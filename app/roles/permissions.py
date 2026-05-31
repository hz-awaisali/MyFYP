"""Canonical permission catalog and default role -> permission mapping.

Permissions are data, not hardcoded into routes. Routes declare the permission
they require via the ``require_permissions(...)`` dependency.
"""

from app.common.enums import RoleName

# code -> human description
PERMISSIONS: dict[str, str] = {
    "create_application": "Create and submit applications",
    "view_own_applications": "View own applications",
    "view_department_applications": "View applications for own department",
    "view_all_applications": "View all applications in the system",
    "approve_application": "Approve / act on applications in a workflow step",
    "manage_application_categories": "Create and configure application categories and forms",
    "manage_workflows": "Create and configure workflow definitions",
    "manage_departments": "Create and manage departments and programs",
    "manage_users": "Approve, suspend and manage user accounts",
    "manage_roles": "Manage roles and permissions",
    "manage_attendance": "Create sessions and manage attendance",
    "view_attendance": "View attendance records and reports",
    "view_analytics": "View analytics and dashboards",
    "manage_settings": "Manage system settings",
    "use_ai_assistant": "Use the AI application-writing assistant",
}

# Default permissions granted to each role on seed.
ROLE_PERMISSIONS: dict[RoleName, list[str]] = {
    RoleName.SUPER_ADMIN: list(PERMISSIONS.keys()),
    RoleName.STUDENT: [
        "create_application",
        "view_own_applications",
        "view_attendance",
        "use_ai_assistant",
    ],
    RoleName.HOD: [
        "view_department_applications",
        "approve_application",
        "view_analytics",
        "manage_attendance",
        "view_attendance",
    ],
    RoleName.HOD_ASSISTANT: [
        "view_department_applications",
        "approve_application",
        "view_attendance",
    ],
    RoleName.EXAMINATION_OFFICER: [
        "view_department_applications",
        "approve_application",
        "view_analytics",
    ],
    RoleName.REGISTRAR_OFFICER: [
        "view_all_applications",
        "approve_application",
        "view_analytics",
    ],
    RoleName.IT_OFFICER: [
        "view_department_applications",
        "approve_application",
    ],
    RoleName.TRANSPORT_OFFICER: [
        "view_department_applications",
        "approve_application",
    ],
    RoleName.TREASURER_OFFICER: [
        "view_department_applications",
        "approve_application",
    ],
}

ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.SUPER_ADMIN: "Full system access",
    RoleName.STUDENT: "Submits applications and views own records",
    RoleName.HOD: "Head of Department",
    RoleName.HOD_ASSISTANT: "Assists the Head of Department",
    RoleName.EXAMINATION_OFFICER: "Handles examination-related applications",
    RoleName.REGISTRAR_OFFICER: "Registrar office",
    RoleName.IT_OFFICER: "IT department officer",
    RoleName.TRANSPORT_OFFICER: "Transport department officer",
    RoleName.TREASURER_OFFICER: "Treasury / finance officer",
}
