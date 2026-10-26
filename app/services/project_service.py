import math
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceRole
from app.models.project import Project, ProjectStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.audit_repository import AuditRepository
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.audit_repo = AuditRepository(db)

    def create_project(self, project_in: ProjectCreate, current_user: User) -> ProjectResponse:
        workspace = self.workspace_repo.get_by_id(project_in.workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", project_in.workspace_id)

        # Check permissions: User must be Admin or Project Manager in the workspace, or system Admin
        role = self.workspace_repo.get_user_role(project_in.workspace_id, current_user.id)
        if current_user.role != UserRole.ADMIN and role not in (
            WorkspaceRole.ADMIN,
            WorkspaceRole.PROJECT_MANAGER,
        ):
            raise ForbiddenException(
                "You must be a Workspace Admin or Project Manager to create projects"
            )

        project = Project(
            workspace_id=project_in.workspace_id,
            name=project_in.name,
            description=project_in.description,
            status=project_in.status,
            created_by_id=current_user.id,
        )
        project = self.project_repo.create(project)

        self.audit_repo.log(
            action="CREATE",
            entity_type="project",
            entity_id=project.id,
            actor_id=current_user.id,
            changes={"name": project.name, "workspace_id": project.workspace_id},
        )

        return self._to_response(project)

    def get_project(self, project_id: int, current_user: User) -> ProjectResponse:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        is_admin = current_user.role == UserRole.ADMIN
        if not self.project_repo.user_has_access(project_id, current_user.id, is_admin=is_admin):
            raise ForbiddenException("You do not have access to this project")

        return self._to_response(project)

    def update_project(
        self,
        project_id: int,
        project_in: ProjectUpdate,
        current_user: User,
    ) -> ProjectResponse:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        role = self.workspace_repo.get_user_role(project.workspace_id, current_user.id)
        is_creator = project.created_by_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN

        if not is_admin and not is_creator and role not in (
            WorkspaceRole.ADMIN,
            WorkspaceRole.PROJECT_MANAGER,
        ):
            raise ForbiddenException("You do not have permission to modify this project")

        changes = {}
        if project_in.name is not None and project_in.name != project.name:
            changes["name"] = {"old": project.name, "new": project_in.name}
            project.name = project_in.name
        if project_in.description is not None and project_in.description != project.description:
            changes["description"] = {"old": project.description, "new": project_in.description}
            project.description = project_in.description
        if project_in.status is not None and project_in.status != project.status:
            changes["status"] = {"old": project.status.value, "new": project_in.status.value}
            project.status = project_in.status

        project = self.project_repo.update(project)

        if changes:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="project",
                entity_id=project.id,
                actor_id=current_user.id,
                changes=changes,
            )

        return self._to_response(project)

    def delete_project(self, project_id: int, current_user: User) -> None:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        role = self.workspace_repo.get_user_role(project.workspace_id, current_user.id)
        is_creator = project.created_by_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN

        if not is_admin and not is_creator and role != WorkspaceRole.ADMIN:
            raise ForbiddenException("Only workspace administrators or the project creator can delete this project")

        self.audit_repo.log(
            action="DELETE",
            entity_type="project",
            entity_id=project.id,
            actor_id=current_user.id,
            changes={"name": project.name},
        )
        self.project_repo.delete(project)

    def list_projects(
        self,
        current_user: User,
        workspace_id: Optional[int] = None,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ProjectListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        skip = (page - 1) * page_size
        is_admin = current_user.role == UserRole.ADMIN

        items, total = self.project_repo.filter_and_paginate(
            user_id=current_user.id,
            is_admin=is_admin,
            workspace_id=workspace_id,
            status=status,
            search=search,
            skip=skip,
            limit=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        responses = [self._to_response(p) for p in items]

        return ProjectListResponse(
            items=responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def _to_response(self, project: Project) -> ProjectResponse:
        total_tasks, completed_tasks, completion_pct = self.project_repo.get_project_stats(project.id)
        res = ProjectResponse.model_validate(project)
        res.task_count = total_tasks
        res.completed_task_count = completed_tasks
        res.completion_percentage = completion_pct
        return res
