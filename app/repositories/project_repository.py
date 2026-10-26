from typing import Optional, List, Tuple
from sqlalchemy import select, or_, func, and_
from sqlalchemy.orm import Session
from app.models.project import Project, ProjectStatus
from app.models.workspace import Workspace, WorkspaceMember
from app.models.task import Task, TaskStatus


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project: Project) -> Project:
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()

    def user_has_access(self, project_id: int, user_id: int, is_admin: bool = False) -> bool:
        if is_admin:
            return True
        project = self.get_by_id(project_id)
        if not project:
            return False
        
        # Check if user is owner of workspace or member of workspace
        member = self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == project.workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if member:
            return True

        workspace = self.db.execute(
            select(Workspace).where(
                Workspace.id == project.workspace_id,
                Workspace.owner_id == user_id,
            )
        ).scalar_one_or_none()
        return workspace is not None

    def filter_and_paginate(
        self,
        user_id: int,
        is_admin: bool = False,
        workspace_id: Optional[int] = None,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Project], int]:
        query = select(Project).join(Workspace, Project.workspace_id == Workspace.id)
        
        if not is_admin:
            query = query.outerjoin(
                WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id
            ).where(
                or_(
                    Workspace.owner_id == user_id,
                    WorkspaceMember.user_id == user_id,
                )
            )

        if workspace_id:
            query = query.where(Project.workspace_id == workspace_id)
        if status:
            query = query.where(Project.status == status)
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Project.name.ilike(search_filter),
                    Project.description.ilike(search_filter),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Paginated items
        items_query = query.distinct().order_by(Project.created_at.desc()).offset(skip).limit(limit)
        items = list(self.db.execute(items_query).scalars().all())

        return items, total

    def get_project_stats(self, project_id: int) -> Tuple[int, int, float]:
        """Returns (total_tasks, completed_tasks, completion_percentage)."""
        total = self.db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        ).scalar_one()

        if total == 0:
            return 0, 0, 0.0

        completed = self.db.execute(
            select(func.count(Task.id)).where(
                Task.project_id == project_id,
                Task.status == TaskStatus.COMPLETED,
            )
        ).scalar_one()

        percentage = round((completed / total) * 100.0, 2)
        return total, completed, percentage
