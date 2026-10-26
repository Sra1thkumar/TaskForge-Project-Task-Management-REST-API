import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.report import (
    ProductivitySummaryResponse,
    StatusBreakdown,
    PriorityBreakdown,
    AssigneeProductivity,
    ProjectProductivity,
    AuditLogResponse,
)
from app.repositories.task_repository import TaskRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.audit_repository import AuditRepository


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.audit_repo = AuditRepository(db)

    def generate_summary(
        self,
        current_user: User,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> ProductivitySummaryResponse:
        is_admin = current_user.role == UserRole.ADMIN
        tasks = self.task_repo.get_all_accessible_tasks(
            user_id=current_user.id,
            is_admin=is_admin,
            workspace_id=workspace_id,
            project_id=project_id,
        )

        total = len(tasks)
        now = datetime.now(timezone.utc)

        status_counts = {s.value: 0 for s in TaskStatus}
        priority_counts = {p.value: 0 for p in TaskPriority}

        completed_count = 0
        overdue_count = 0

        # Aggregations by assignee and project
        assignee_stats: Dict[int, Dict[str, Any]] = {}
        project_stats: Dict[int, Dict[str, Any]] = {}

        for task in tasks:
            status_val = task.status.value
            priority_val = task.priority.value
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
            priority_counts[priority_val] = priority_counts.get(priority_val, 0) + 1

            is_completed = task.status == TaskStatus.COMPLETED
            if is_completed:
                completed_count += 1

            is_overdue = False
            if task.due_date and not is_completed:
                due_utc = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
                if due_utc < now:
                    overdue_count += 1
                    is_overdue = True

            # Assignee tracking
            if task.assignee:
                uid = task.assignee.id
                if uid not in assignee_stats:
                    assignee_stats[uid] = {
                        "user_id": uid,
                        "user_name": task.assignee.full_name or task.assignee.email,
                        "user_email": task.assignee.email,
                        "total_assigned": 0,
                        "completed": 0,
                        "pending": 0,
                        "overdue": 0,
                    }
                assignee_stats[uid]["total_assigned"] += 1
                if is_completed:
                    assignee_stats[uid]["completed"] += 1
                else:
                    assignee_stats[uid]["pending"] += 1
                if is_overdue:
                    assignee_stats[uid]["overdue"] += 1

            # Project tracking
            if task.project:
                pid = task.project.id
                if pid not in project_stats:
                    project_stats[pid] = {
                        "project_id": pid,
                        "project_name": task.project.name,
                        "total_tasks": 0,
                        "completed_tasks": 0,
                        "overdue_tasks": 0,
                    }
                project_stats[pid]["total_tasks"] += 1
                if is_completed:
                    project_stats[pid]["completed_tasks"] += 1
                if is_overdue:
                    project_stats[pid]["overdue_tasks"] += 1

        pending_count = total - completed_count
        completion_rate = round((completed_count / total * 100.0), 2) if total > 0 else 0.0

        # Build assignee list
        assignee_breakdown = []
        for s in assignee_stats.values():
            tot = s["total_assigned"]
            comp = s["completed"]
            rate = round((comp / tot * 100.0), 2) if tot > 0 else 0.0
            assignee_breakdown.append(
                AssigneeProductivity(
                    user_id=s["user_id"],
                    user_name=s["user_name"],
                    user_email=s["user_email"],
                    total_assigned=tot,
                    completed=comp,
                    pending=s["pending"],
                    overdue=s["overdue"],
                    completion_rate=rate,
                )
            )

        # Build project list
        project_breakdown = []
        for p in project_stats.values():
            tot = p["total_tasks"]
            comp = p["completed_tasks"]
            pct = round((comp / tot * 100.0), 2) if tot > 0 else 0.0
            project_breakdown.append(
                ProjectProductivity(
                    project_id=p["project_id"],
                    project_name=p["project_name"],
                    total_tasks=tot,
                    completed_tasks=comp,
                    overdue_tasks=p["overdue_tasks"],
                    completion_percentage=pct,
                )
            )

        return ProductivitySummaryResponse(
            total_tasks=total,
            completed_tasks=completed_count,
            pending_tasks=pending_count,
            overdue_tasks=overdue_count,
            completion_rate=completion_rate,
            status_breakdown=StatusBreakdown(**status_counts),
            priority_breakdown=PriorityBreakdown(**priority_counts),
            assignee_breakdown=assignee_breakdown,
            project_breakdown=project_breakdown,
        )

    def export_tasks_csv(
        self,
        current_user: User,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> str:
        is_admin = current_user.role == UserRole.ADMIN
        tasks = self.task_repo.get_all_accessible_tasks(
            user_id=current_user.id,
            is_admin=is_admin,
            workspace_id=workspace_id,
            project_id=project_id,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Header
        writer.writerow([
            "Task ID",
            "Title",
            "Description",
            "Project ID",
            "Project Name",
            "Assignee Name",
            "Assignee Email",
            "Priority",
            "Status",
            "Due Date",
            "Created At",
        ])

        for t in tasks:
            writer.writerow([
                t.id,
                t.title,
                t.description or "",
                t.project_id,
                t.project.name if t.project else "",
                t.assignee.full_name if t.assignee and t.assignee.full_name else "",
                t.assignee.email if t.assignee else "",
                t.priority.value,
                t.status.value,
                t.due_date.isoformat() if t.due_date else "",
                t.created_at.isoformat() if t.created_at else "",
            ])

        return output.getvalue()

    def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditLogResponse], int]:
        logs, total = self.audit_repo.list(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            skip=skip,
            limit=limit,
        )
        responses = []
        for log in logs:
            parsed_changes = json.loads(log.changes) if log.changes else None
            responses.append(
                AuditLogResponse(
                    id=log.id,
                    actor_id=log.actor_id,
                    actor=log.actor,
                    action=log.action,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    changes=parsed_changes,
                    created_at=log.created_at,
                )
            )
        return responses, total
