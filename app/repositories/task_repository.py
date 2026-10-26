from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, or_, func, and_, desc, asc
from sqlalchemy.orm import Session
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.project import Project
from app.models.workspace import Workspace, WorkspaceMember


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: int) -> Optional[Task]:
        return self.db.execute(
            select(Task).where(Task.id == task_id)
        ).scalar_one_or_none()

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task) -> Task:
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.commit()

    def _accessible_tasks_query(self, user_id: int, is_admin: bool = False):
        query = (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(Workspace, Project.workspace_id == Workspace.id)
        )
        if not is_admin:
            query = query.outerjoin(
                WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id
            ).where(
                or_(
                    Workspace.owner_id == user_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        return query

    def filter_and_paginate(
        self,
        user_id: int,
        is_admin: bool = False,
        project_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        due_date_before: Optional[datetime] = None,
        due_date_after: Optional[datetime] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Task], int]:
        query = self._accessible_tasks_query(user_id, is_admin)

        if project_id:
            query = query.where(Task.project_id == project_id)
        if workspace_id:
            query = query.where(Project.workspace_id == workspace_id)
        if assignee_id:
            query = query.where(Task.assignee_id == assignee_id)
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if due_date_before:
            query = query.where(Task.due_date <= due_date_before)
        if due_date_after:
            query = query.where(Task.due_date >= due_date_after)
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Task.title.ilike(search_filter),
                    Task.description.ilike(search_filter),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Sorting
        sort_column = getattr(Task, sort_by, Task.created_at)
        order_fn = desc if sort_order.lower() == "desc" else asc
        items_query = query.distinct().order_by(order_fn(sort_column)).offset(skip).limit(limit)
        items = list(self.db.execute(items_query).scalars().all())

        return items, total

    def get_all_accessible_tasks(
        self,
        user_id: int,
        is_admin: bool = False,
        project_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
    ) -> List[Task]:
        query = self._accessible_tasks_query(user_id, is_admin)
        if project_id:
            query = query.where(Task.project_id == project_id)
        if workspace_id:
            query = query.where(Project.workspace_id == workspace_id)
        return list(self.db.execute(query.distinct()).scalars().all())

    def get_approaching_deadline_tasks(self, within_hours: int = 24) -> List[Task]:
        """Fetch tasks whose deadline is within the next `within_hours` and not yet completed."""
        now = datetime.now(timezone.utc)
        target = now + datetime.resolution * 0  # base
        import datetime as dt
        deadline_threshold = now + dt.timedelta(hours=within_hours)

        query = select(Task).where(
            Task.status != TaskStatus.COMPLETED,
            Task.due_date.isnot(None),
            Task.due_date >= now,
            Task.due_date <= deadline_threshold,
            Task.assignee_id.isnot(None),
        )
        return list(self.db.execute(query).scalars().all())
