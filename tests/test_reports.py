import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.models.project import Project
from app.models.user import User


def test_productivity_summary(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
    member_user: User,
):
    future_date = datetime.now(timezone.utc) + timedelta(days=2)
    # Create a task
    client.post(
        "/api/v1/tasks/",
        json={
            "project_id": sample_project.id,
            "title": "Task For Summary",
            "priority": "high",
            "status": "todo",
            "assignee_id": member_user.id,
            "due_date": future_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    response = client.get(
        "/api/v1/reports/summary",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "completed_tasks" in data
    assert "pending_tasks" in data
    assert "completion_rate" in data
    assert "status_breakdown" in data
    assert "priority_breakdown" in data
    assert "assignee_breakdown" in data
    assert "project_breakdown" in data
    assert data["total_tasks"] >= 1


def test_export_tasks_csv(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    future_date = datetime.now(timezone.utc) + timedelta(days=2)
    client.post(
        "/api/v1/tasks/",
        json={
            "project_id": sample_project.id,
            "title": "CSV Task Test",
            "priority": "medium",
            "status": "in_progress",
            "due_date": future_date.isoformat(),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    response = client.get(
        "/api/v1/reports/export/csv",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers.get("Content-Disposition", "")
    content = response.text
    assert "Task ID,Title,Description" in content
    assert "CSV Task Test" in content


def test_audit_logs(
    client: TestClient,
    manager_token: str,
    sample_project: Project,
):
    # Perform an update to generate an audit log
    client.patch(
        f"/api/v1/projects/{sample_project.id}",
        json={"name": "Audit Logging Verified"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    response = client.get(
        "/api/v1/reports/audit-logs",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
    actions = [log["action"] for log in logs]
    assert "UPDATE" in actions or "CREATE" in actions
