"""Workflow engine transition tests."""

import pytest

from app.applications.models import Application, ApplicationCategory
from app.common.enums import (
    ApplicationStatus,
    RoleName,
    UserStatus,
    WorkflowActionType,
)
from app.core.security import hash_password
from app.departments.models import Department
from app.roles.repository import RoleRepository
from app.users.models import User
from app.users.repository import UserRepository
from app.workflows.engine import WorkflowEngine
from app.workflows.models import WorkflowDefinition, WorkflowStep

pytestmark = pytest.mark.asyncio


async def _setup(db):
    roles = {r.name: r for r in await RoleRepository(db).list_all()}

    dept = Department(name="CS & IT", code="CSIT")
    db.add(dept)
    await db.flush()

    hod = User(
        email="hod@uni.edu",
        hashed_password=hash_password("x"),
        full_name="HOD",
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.HOD.value].id,
        department_id=dept.id,
    )
    exam = User(
        email="exam@uni.edu",
        hashed_password=hash_password("x"),
        full_name="Exam Officer",
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.EXAMINATION_OFFICER.value].id,
        department_id=dept.id,
    )
    student = User(
        email="stud@uni.edu",
        hashed_password=hash_password("x"),
        full_name="Student",
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.STUDENT.value].id,
    )
    db.add_all([hod, exam, student])
    await db.flush()

    wf = WorkflowDefinition(name="Transcript WF")
    db.add(wf)
    await db.flush()
    db.add_all(
        [
            WorkflowStep(
                workflow_id=wf.id,
                step_order=1,
                name="HOD",
                role_id=roles[RoleName.HOD.value].id,
                department_id=dept.id,
            ),
            WorkflowStep(
                workflow_id=wf.id,
                step_order=2,
                name="Examination",
                role_id=roles[RoleName.EXAMINATION_OFFICER.value].id,
                is_final=True,
            ),
        ]
    )
    await db.flush()

    category = ApplicationCategory(name="Transcript", department_id=dept.id, workflow_id=wf.id)
    db.add(category)
    await db.flush()

    application = Application(
        category_id=category.id,
        student_id=student.id,
        department_id=dept.id,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.flush()

    users = UserRepository(db)
    return {
        "wf": wf,
        "application": application,
        "hod": await users.get_with_relations(hod.id),
        "exam": await users.get_with_relations(exam.id),
    }


async def test_workflow_advances_then_completes(db, seeded):
    ctx = await _setup(db)
    engine = WorkflowEngine(db)
    application = ctx["application"]

    instance = await engine.start(application_id=application.id, workflow_id=ctx["wf"].id)
    assert instance.current_step_id is not None

    # HOD approves -> forwarded to next step.
    result = await engine.act(
        application=application,
        instance=instance,
        user=ctx["hod"],
        action=WorkflowActionType.APPROVE,
    )
    assert result.new_status == ApplicationStatus.FORWARDED
    assert not result.is_complete

    # Examination officer approves the final step -> completed.
    result = await engine.act(
        application=application,
        instance=instance,
        user=ctx["exam"],
        action=WorkflowActionType.APPROVE,
    )
    assert result.new_status == ApplicationStatus.COMPLETED
    assert result.is_complete
    assert instance.current_step_id is None


async def test_unauthorized_actor_cannot_act(db, seeded):
    ctx = await _setup(db)
    engine = WorkflowEngine(db)
    application = ctx["application"]
    instance = await engine.start(application_id=application.id, workflow_id=ctx["wf"].id)

    # The examination officer is not the actor for the first (HOD) step.
    from app.core.exceptions import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await engine.act(
            application=application,
            instance=instance,
            user=ctx["exam"],
            action=WorkflowActionType.APPROVE,
        )


async def test_reject_completes_as_rejected(db, seeded):
    ctx = await _setup(db)
    engine = WorkflowEngine(db)
    application = ctx["application"]
    instance = await engine.start(application_id=application.id, workflow_id=ctx["wf"].id)

    result = await engine.act(
        application=application,
        instance=instance,
        user=ctx["hod"],
        action=WorkflowActionType.REJECT,
        remarks="Incomplete documents",
    )
    assert result.new_status == ApplicationStatus.REJECTED
    assert result.is_complete
