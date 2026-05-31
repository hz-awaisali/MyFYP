"""RBAC / permission guard tests."""

import pytest

API = "/api/v1"


async def _approved_student_token(client, admin_token, email="rbac.student@uni.edu"):
    reg = await client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "full_name": "RBAC Student",
            "registration_number": "FA21-BSCS-900",
        },
    )
    user_id = reg.json()["id"]
    await client.patch(
        f"{API}/users/{user_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": email, "password": "Password123"}
    )
    return login.json()["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_unauthenticated_is_rejected(client):
    resp = await client.get(f"{API}/users")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_student_cannot_manage_users(client, admin_token):
    token = await _approved_student_token(client, admin_token)
    resp = await client.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_manage_users(client, admin_token):
    resp = await client.get(f"{API}/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200, resp.text
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_super_admin_can_create_department(client, admin_token):
    resp = await client.post(
        f"{API}/departments",
        json={"name": "Electrical Engineering", "code": "EE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["code"] == "EE"
