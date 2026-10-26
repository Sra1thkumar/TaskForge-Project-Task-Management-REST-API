import pytest
from fastapi.testclient import TestClient
from app.models.workspace import Workspace
from app.models.project import Project


def test_create_project_success(
    client: TestClient,
    manager_token: str,
    sample_workspace: Workspace,
):
    payload = {
        "workspace_id": sample_workspace.id,
        "name": "Cloud Infrastructure",
        "description": "Kubernetes and Helm charts setup",
        "status": "planning",
    }
    response = client.post(
        "/api/v1/projects/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cloud Infrastructure"
    assert data["workspace_id"] == sample_workspace.id
    assert data["completion_percentage"] == 0.0


def test_create_project_forbidden_for_regular_member(
    client: TestClient,
    member_token: str,
    sample_workspace: Workspace,
):
    payload = {
        "workspace_id": sample_workspace.id,
        "name": "Unauthorized Project Attempt",
        "status": "planning",
    }
    # member_user has role 'member' in sample_workspace
    response = client.post(
        "/api/v1/projects/",
        json=payload,
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403
    assert "Workspace Admin or Project Manager" in response.json()["detail"]


def test_get_project_with_stats(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    response = client.get(
        f"/api/v1/projects/{sample_project.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_project.id
    assert "completion_percentage" in data
    assert "task_count" in data


def test_update_project(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    payload = {
        "name": "Backend Core V2",
        "status": "in_progress",
    }
    response = client.patch(
        f"/api/v1/projects/{sample_project.id}",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Backend Core V2"
    assert response.json()["status"] == "in_progress"


def test_project_isolation_forbidden(
    client: TestClient,
    other_token: str,
    sample_project: Project,
):
    response = client.get(
        f"/api/v1/projects/{sample_project.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403
    assert "do not have access" in response.json()["detail"]


def test_delete_project(
    client: TestClient,
    manager_token: str,
    sample_workspace: Workspace,
):
    # Create project to delete
    create_res = client.post(
        "/api/v1/projects/",
        json={"workspace_id": sample_workspace.id, "name": "Temp Project", "status": "planning"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    proj_id = create_res.json()["id"]

    del_res = client.delete(
        f"/api/v1/projects/{proj_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(
        f"/api/v1/projects/{proj_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert get_res.status_code == 404
