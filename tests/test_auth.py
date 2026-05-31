"""Authentication and account-lifecycle tests."""

import pytest

API = "/api/v1"


@pytest.mark.asyncio
async def test_register_creates_pending_account(client):
    resp = await client.post(
        f"{API}/auth/register",
        json={
            "email": "student1@uni.edu",
            "password": "Password123",
            "full_name": "Student One",
            "registration_number": "FA21-BSCS-001",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["email"] == "student1@uni.edu"


@pytest.mark.asyncio
async def test_pending_user_cannot_login(client):
    await client.post(
        f"{API}/auth/register",
        json={
            "email": "student2@uni.edu",
            "password": "Password123",
            "full_name": "Student Two",
            "registration_number": "FA21-BSCS-002",
        },
    )
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "student2@uni.edu", "password": "Password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_approval_then_login_and_refresh(client, admin_token):
    reg = await client.post(
        f"{API}/auth/register",
        json={
            "email": "student3@uni.edu",
            "password": "Password123",
            "full_name": "Student Three",
            "registration_number": "FA21-BSCS-003",
        },
    )
    user_id = reg.json()["id"]

    approve = await client.patch(
        f"{API}/users/{user_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve.status_code == 200, approve.text

    login = await client.post(
        f"{API}/auth/login",
        json={"email": "student3@uni.edu", "password": "Password123"},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()["tokens"]
    assert tokens["access_token"] and tokens["refresh_token"]

    refresh = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]


@pytest.mark.asyncio
async def test_invalid_credentials(client):
    resp = await client.post(
        f"{API}/auth/login",
        json={"email": "nobody@uni.edu", "password": "wrong"},
    )
    assert resp.status_code == 401
