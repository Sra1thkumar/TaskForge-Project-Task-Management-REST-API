import pytest
from fastapi.testclient import TestClient
from app.models.workspace import Workspace


def test_create_workspace(client: TestClient, manager_token: str):
    payload = {
        "name": "Design Systems Inc",
        "description": "UI/UX and design components",
    }
    response = client.post(
        "/api/v1/workspaces/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Design Systems Inc"
    assert data["description"] == "UI/UX and design components"
    assert "id" in data


def test_list_workspaces(client: TestClient, manager_token: str, sample_workspace: Workspace):
    response = client.get(
        "/api/v1/workspaces/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) >= 1
    ids = [w["id"] for w in workspaces]
    assert sample_workspace.id in ids


def test_workspace_isolation_forbidden(
    client: TestClient,
    other_token: str,
    sample_workspace: Workspace,
):
    # Other user is not a member of sample_workspace
    response = client.get(
        f"/api/v1/workspaces/{sample_workspace.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403
    assert "do not have access" in response.json()["detail"]


def test_add_workspace_member(
    client: TestClient,
    manager_token: str,
    sample_workspace: Workspace,
    other_user,
):
    payload = {
        "user_email": other_user.email,
        "role": "member",
    }
    response = client.post(
        f"/api/v1/workspaces/{sample_workspace.id}/members",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == other_user.id

    # Now verify members list
    members_res = client.get(
        f"/api/v1/workspaces/{sample_workspace.id}/members",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert members_res.status_code == 200
    member_user_ids = [m["user_id"] for m in members_res.json()]
    assert other_user.id in member_user_ids


def test_update_workspace(
    client: TestClient,
    manager_token: str,
    sample_workspace: Workspace,
):
    update_data = {"name": "Updated Alpha Engineering"}
    response = client.patch(
        f"/api/v1/workspaces/{sample_workspace.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Alpha Engineering"
