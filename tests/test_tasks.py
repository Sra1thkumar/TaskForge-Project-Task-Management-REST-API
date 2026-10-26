from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.models.project import Project
from app.models.user import User


def test_create_task_success(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
    member_user: User,
):
    future_date = datetime.now(timezone.utc) + timedelta(days=5)
    payload = {
        "project_id": sample_project.id,
        "title": "Build Authentication Endpoints",
        "description": "Implement JWT and Argon2 hashing",
        "priority": "high",
        "status": "todo",
        "due_date": future_date.isoformat(),
        "assignee_id": member_user.id,
    }
    response = client.post(
        "/api/v1/tasks/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Build Authentication Endpoints"
    assert data["priority"] == "high"
    assert data["status"] == "todo"
    assert data["assignee_id"] == member_user.id
    assert data["is_overdue"] is False


def test_create_task_past_deadline_rejected(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    payload = {
        "project_id": sample_project.id,
        "title": "Invalid Past Task",
        "due_date": past_date.isoformat(),
    }
    response = client.post(
        "/api/v1/tasks/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 422 or response.status_code == 400


def test_create_task_outsider_assignee_rejected(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
    other_user: User,
):
    future_date = datetime.now(timezone.utc) + timedelta(days=3)
    payload = {
        "project_id": sample_project.id,
        "title": "Assign To Outsider",
        "assignee_id": other_user.id,
        "due_date": future_date.isoformat(),
    }
    response = client.post(
        "/api/v1/tasks/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400
    assert "member of the project workspace" in response.json()["detail"]


def test_task_status_transitions_and_project_completion(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    # 1. Create task
    future_date = datetime.now(timezone.utc) + timedelta(days=2)
    res = client.post(
        f"/api/v1/projects/{sample_project.id}/tasks",
        json={
            "project_id": sample_project.id,
            "title": "Test Completion Flow",
            "status": "todo",
            "due_date": future_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res.status_code == 201
    task_id = res.json()["id"]

    # 2. Transition TODO -> IN_PROGRESS
    res_progress = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res_progress.status_code == 200
    assert res_progress.json()["status"] == "in_progress"

    # 3. Transition IN_PROGRESS -> COMPLETED
    res_completed = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert res_completed.status_code == 200
    assert res_completed.json()["status"] == "completed"

    # 4. Check project completion percentage is updated!
    proj_res = client.get(
        f"/api/v1/projects/{sample_project.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert proj_res.status_code == 200
    assert proj_res.json()["completion_percentage"] == 100.0


def test_filter_and_search_tasks(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    future_date = datetime.now(timezone.utc) + timedelta(days=2)
    # Create two tasks
    client.post(
        "/api/v1/tasks/",
        json={
            "project_id": sample_project.id,
            "title": "Alpha Deployment Bug",
            "priority": "urgent",
            "status": "todo",
            "due_date": future_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    client.post(
        "/api/v1/tasks/",
        json={
            "project_id": sample_project.id,
            "title": "Documentation Revision",
            "priority": "low",
            "status": "todo",
            "due_date": future_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    # Filter by priority=urgent
    urgent_res = client.get(
        "/api/v1/tasks/?priority=urgent",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert urgent_res.status_code == 200
    items = urgent_res.json()["items"]
    assert all(i["priority"] == "urgent" for i in items)

    # Search by keyword
    search_res = client.get(
        "/api/v1/tasks/?search=Documentation",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert search_res.status_code == 200
    assert len(search_res.json()["items"]) >= 1
    assert "Documentation" in search_res.json()["items"][0]["title"]
