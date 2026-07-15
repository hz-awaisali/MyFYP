"""Tests for Analytics, Dashboard, AI Assistant, SLA, and PDF Export."""

import pytest
import uuid
from datetime import datetime, timezone
from app.common.enums import (
    ApplicationStatus,
    RoleName,
    UserStatus,
    WorkflowActionType,
    FieldType,
)
from app.applications.models import Application, ApplicationCategory, ApplicationForm, ApplicationField, ApplicationResponse
from app.departments.models import Department
from app.users.models import User
from app.roles.repository import RoleRepository
from app.core.security import hash_password
from app.workflows.models import WorkflowDefinition, WorkflowStep, WorkflowInstance, WorkflowAction

pytestmark = pytest.mark.asyncio

API = "/api/v1"


async def _setup_data(db):
    roles = {r.name: r for r in await RoleRepository(db).list_all()}

    # Create department
    dept = Department(name="Computer Science", code="CS")
    db.add(dept)
    await db.flush()

    # Create users
    hod = User(
        email="hod.cs@uni.edu",
        hashed_password=hash_password("Password123"),
        full_name="CS HOD",
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.HOD.value].id,
        department_id=dept.id,
    )
    student = User(
        email="student.cs@uni.edu",
        hashed_password=hash_password("Password123"),
        full_name="CS Student",
        status=UserStatus.APPROVED,
        role_id=roles[RoleName.STUDENT.value].id,
        department_id=dept.id,
    )
    db.add_all([hod, student])
    await db.flush()

    # Create Workflow Definition
    wf = WorkflowDefinition(name="Test Workflow")
    db.add(wf)
    await db.flush()

    step1 = WorkflowStep(
        workflow_id=wf.id,
        step_order=1,
        name="HOD Approval",
        role_id=roles[RoleName.HOD.value].id,
        department_id=dept.id,
    )
    db.add(step1)
    await db.flush()

    # Create Application Category and Form
    category = ApplicationCategory(name="Semester Freeze", department_id=dept.id, workflow_id=wf.id)
    db.add(category)
    await db.flush()

    form = ApplicationForm(category_id=category.id, name="Freeze Form", is_active=True)
    db.add(form)
    await db.flush()

    field = ApplicationField(
        form_id=form.id,
        key="reason",
        label="Reason for Freeze",
        field_type=FieldType.TEXT,
        is_required=True,
    )
    db.add(field)
    await db.flush()

    # Create active applications
    app_draft = Application(
        category_id=category.id,
        form_id=form.id,
        student_id=student.id,
        department_id=dept.id,
        status=ApplicationStatus.DRAFT,
        subject="Draft Request",
    )
    app_pending = Application(
        category_id=category.id,
        form_id=form.id,
        student_id=student.id,
        department_id=dept.id,
        status=ApplicationStatus.PENDING,
        subject="Pending Request",
    )
    db.add_all([app_draft, app_pending])
    await db.flush()

    # Create workflow instance for pending
    wf_inst = WorkflowInstance(
        workflow_id=wf.id,
        application_id=app_pending.id,
        current_step_id=step1.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(wf_inst)
    await db.flush()

    # Perform action on pending (approve/resolve it)
    app_approved = Application(
        category_id=category.id,
        form_id=form.id,
        student_id=student.id,
        department_id=dept.id,
        status=ApplicationStatus.APPROVED,
        subject="Approved Request",
    )
    db.add(app_approved)
    await db.flush()

    wf_inst_approved = WorkflowInstance(
        workflow_id=wf.id,
        application_id=app_approved.id,
        current_step_id=None,
        started_at=datetime.now(timezone.utc),
        is_complete=True,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(wf_inst_approved)
    await db.flush()

    # Add workflow actions for the approved workflow to test turnaround times
    action1 = WorkflowAction(
        instance_id=wf_inst_approved.id,
        step_id=step1.id,
        actor_id=hod.id,
        action=WorkflowActionType.APPROVE,
        remarks="Approved",
        from_status=ApplicationStatus.PENDING.value,
        to_status=ApplicationStatus.APPROVED.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(action1)
    await db.flush()

    await db.commit()

    return {
        "dept": dept,
        "hod": hod,
        "student": student,
        "category": category,
        "form": form,
        "field": field,
        "app_draft": app_draft,
        "app_pending": app_pending,
        "app_approved": app_approved,
        "wf_inst": wf_inst,
        "wf_inst_approved": wf_inst_approved,
    }


async def _get_token(client, email, password="Password123"):
    login = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    return login.json()["tokens"]["access_token"]


async def test_analytics_endpoints(client, db, seeded):
    data = await _setup_data(db)
    admin_token = await _get_token(client, "admin@university.edu", "Admin@12345")
    hod_token = await _get_token(client, data["hod"].email)

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_hod = {"Authorization": f"Bearer {hod_token}"}

    # 1. Overview
    resp = await client.get(f"{API}/analytics/overview", headers=headers_admin)
    assert resp.status_code == 200, resp.text
    overview = resp.json()
    assert overview["total"] == 3
    assert overview["approved"] == 1
    assert overview["pending"] == 1

    # 2. By Department
    resp = await client.get(f"{API}/analytics/by-department", headers=headers_admin)
    assert resp.status_code == 200
    by_dept = resp.json()["items"]
    assert len(by_dept) > 0
    assert by_dept[0]["department_name"] == "Computer Science"

    # 3. Turnaround
    resp = await client.get(f"{API}/analytics/turnaround", headers=headers_admin)
    assert resp.status_code == 200
    turnaround = resp.json()
    assert len(turnaround) > 0
    assert turnaround[0]["step_name"] == "HOD Approval"

    # 4. Approval Rate
    resp = await client.get(f"{API}/analytics/approval-rate", headers=headers_admin)
    assert resp.status_code == 200
    app_rate = resp.json()
    assert app_rate["overall"]["approved"] == 1

    # 5. Bottlenecks
    resp = await client.get(f"{API}/analytics/bottlenecks", headers=headers_admin)
    assert resp.status_code == 200
    bottlenecks = resp.json()
    assert len(bottlenecks) > 0


async def test_dashboard_endpoints(client, db, seeded):
    data = await _setup_data(db)
    admin_token = await _get_token(client, "admin@university.edu", "Admin@12345")
    student_token = await _get_token(client, data["student"].email)
    hod_token = await _get_token(client, data["hod"].email)

    # Test Admin Summary
    resp = await client.get(f"{API}/dashboard/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["admin_summary"] is not None
    assert summary["admin_summary"]["total"] == 3

    # Test Student Summary
    resp = await client.get(f"{API}/dashboard/summary", headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["student_summary"] is not None

    # Test Approver Summary
    resp = await client.get(f"{API}/dashboard/summary", headers={"Authorization": f"Bearer {hod_token}"})
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["approver_summary"] is not None
    assert summary["approver_summary"]["pending_my_approval_count"] == 1


async def test_ai_draft_generation(client, db, seeded):
    data = await _setup_data(db)
    student_token = await _get_token(client, data["student"].email)

    resp = await client.post(
        f"{API}/applications/ai-draft",
        json={"prompt": "I need to freeze my semester due to health reasons.", "form_id": str(data["form"].id)},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 201, resp.text
    app_draft = resp.json()
    assert app_draft["status"] == "draft"
    assert app_draft["subject"] == "Application Request"
    assert len(app_draft["responses"]) > 0


async def test_sla_checking(client, db, seeded):
    data = await _setup_data(db)
    admin_token = await _get_token(client, "admin@university.edu", "Admin@12345")

    # Force pending step entry time to be far in the past to trigger SLA reminder
    data["wf_inst"].started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db.commit()

    resp = await client.post(
        f"{API}/applications/check-slas",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert "reminders_sent" in result


async def test_pdf_export(client, db, seeded):
    data = await _setup_data(db)
    admin_token = await _get_token(client, "admin@university.edu", "Admin@12345")

    # Add responses to the approved application so PDF contains them
    field = data["field"]
    app_resp = ApplicationResponse(
        application_id=data["app_approved"].id,
        field_id=field.id,
        field_key=field.key,
        value="Medical necessity",
    )
    db.add(app_resp)
    await db.commit()

    resp = await client.get(
        f"{API}/applications/{data['app_approved'].id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0
