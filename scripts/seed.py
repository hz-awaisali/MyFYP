"""Idempotent seed script.

Seeds: permissions, roles + role-permission mappings, the first super admin,
the CS & IT department with its programs, and a demo application category with
a dynamic form and a Transcript Request workflow.

Run with:  python -m scripts.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.applications.models import (
    ApplicationCategory,
    ApplicationField,
    ApplicationForm,
)
from app.common.enums import FieldType, RoleName
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.departments.models import Department, Program
from app.roles.models import Permission, Role
from app.roles.permissions import (
    PERMISSIONS,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
)
from app.users.models import User
from app.workflows.models import WorkflowDefinition, WorkflowStep

PROGRAMS = [
    ("BS Computer Science", "BSCS"),
    ("BS Information Technology", "BSIT"),
    ("BS Artificial Intelligence", "BSAI"),
    ("BS Data Science", "BSDS"),
]


async def seed_permissions(session) -> dict[str, Permission]:
    existing = {p.code: p for p in (await session.execute(select(Permission))).scalars()}
    for code, description in PERMISSIONS.items():
        if code not in existing:
            perm = Permission(code=code, description=description)
            session.add(perm)
            existing[code] = perm
    await session.flush()
    return existing


async def seed_roles(session, perms: dict[str, Permission]) -> dict[str, Role]:
    existing = {}
    # Eager-load permissions so reassigning the collection does not trigger a
    # lazy load in a synchronous context (which breaks under async sessions).
    result = await session.execute(select(Role).options(selectinload(Role.permissions)))
    for role in result.scalars():
        existing[role.name] = role

    for role_name, codes in ROLE_PERMISSIONS.items():
        desired = [perms[c] for c in codes if c in perms]
        role = existing.get(role_name.value)
        if role is None:
            # Set permissions in the constructor while the object is transient.
            role = Role(
                name=role_name.value,
                description=ROLE_DESCRIPTIONS.get(role_name, ""),
                is_system=True,
                permissions=desired,
            )
            session.add(role)
            existing[role_name.value] = role
        else:
            role.permissions = desired
    await session.flush()
    return existing


async def seed_super_admin(session, roles: dict[str, Role]) -> None:
    email = settings.SUPERADMIN_EMAIL.lower()
    found = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if found:
        return
    from app.common.enums import UserStatus

    admin = User(
        email=email,
        hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
        full_name=settings.SUPERADMIN_FULL_NAME,
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.SUPER_ADMIN.value].id,
    )
    session.add(admin)
    await session.flush()


async def seed_department(session) -> Department:
    dept = (
        await session.execute(select(Department).where(Department.code == "CSIT"))
    ).scalar_one_or_none()
    if dept is None:
        dept = Department(name="CS & IT Department", code="CSIT", description="Computing programs")
        session.add(dept)
        await session.flush()

    existing_codes = {
        p.code for p in (await session.execute(select(Program).where(Program.department_id == dept.id))).scalars()
    }
    for name, code in PROGRAMS:
        if code not in existing_codes:
            session.add(Program(name=name, code=code, department_id=dept.id, duration_years=4))
    await session.flush()
    return dept


async def seed_workflow_and_category(session, roles, dept) -> None:
    wf = (
        await session.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.name == "Transcript Request Workflow")
        )
    ).scalar_one_or_none()
    if wf is None:
        wf = WorkflowDefinition(
            name="Transcript Request Workflow",
            description="Student -> HOD -> Examination -> Completed",
        )
        session.add(wf)
        await session.flush()
        session.add_all(
            [
                WorkflowStep(
                    workflow_id=wf.id,
                    step_order=1,
                    name="HOD Approval",
                    role_id=roles[RoleName.HOD.value].id,
                    department_id=dept.id,
                    approval_required=True,
                ),
                WorkflowStep(
                    workflow_id=wf.id,
                    step_order=2,
                    name="Examination Processing",
                    role_id=roles[RoleName.EXAMINATION_OFFICER.value].id,
                    approval_required=True,
                    is_final=True,
                ),
            ]
        )
        await session.flush()

    category = (
        await session.execute(
            select(ApplicationCategory).where(ApplicationCategory.name == "Transcript Request")
        )
    ).scalar_one_or_none()
    if category is None:
        category = ApplicationCategory(
            name="Transcript Request",
            description="Request an official academic transcript",
            department_id=dept.id,
            workflow_id=wf.id,
        )
        session.add(category)
        await session.flush()

        form = ApplicationForm(category_id=category.id, name="Transcript Request Form")
        session.add(form)
        await session.flush()
        session.add_all(
            [
                ApplicationField(
                    form_id=form.id,
                    key="reason",
                    label="Reason for request",
                    field_type=FieldType.TEXTAREA,
                    is_required=True,
                    display_order=1,
                ),
                ApplicationField(
                    form_id=form.id,
                    key="copies",
                    label="Number of copies",
                    field_type=FieldType.NUMBER,
                    is_required=True,
                    validation={"min": 1, "max": 10},
                    display_order=2,
                ),
                ApplicationField(
                    form_id=form.id,
                    key="delivery",
                    label="Delivery method",
                    field_type=FieldType.DROPDOWN,
                    is_required=True,
                    options=["Pickup", "Email", "Postal"],
                    display_order=3,
                ),
            ]
        )
        await session.flush()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        perms = await seed_permissions(session)
        roles = await seed_roles(session, perms)
        await seed_super_admin(session, roles)
        dept = await seed_department(session)
        await seed_workflow_and_category(session, roles, dept)
        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
