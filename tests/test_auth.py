import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    payload = {
        "email": "newuser@workflowpro.io",
        "full_name": "New User",
        "password": "Password123!",
        "role": "member",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@workflowpro.io"
    assert data["user"]["full_name"] == "New User"


def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@workflowpro.io",
        "full_name": "First User",
        "password": "Password123!",
        "role": "member",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_register_short_password(client: TestClient):
    payload = {
        "email": "shortpw@workflowpro.io",
        "full_name": "Short Pw",
        "password": "short",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success(client: TestClient):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logintest@workflowpro.io",
            "full_name": "Login Tester",
            "password": "SecurePassword123!",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@workflowpro.io", "password": "SecurePassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "logintest@workflowpro.io"


def test_login_invalid_password(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@workflowpro.io",
            "password": "CorrectPassword123!",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@workflowpro.io", "password": "IncorrectPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user_me(client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "me_test@workflowpro.io",
            "full_name": "Profile User",
            "password": "SecurePassword123!",
        },
    )
    token = reg.json()["access_token"]

    # Without token -> 401
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    # With token -> 200
    res_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["email"] == "me_test@workflowpro.io"
    assert res_auth.json()["full_name"] == "Profile User"


def test_refresh_token_flow(client: TestClient):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh_test@workflowpro.io",
            "password": "SecurePassword123!",
        },
    )
    refresh_token = reg.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
