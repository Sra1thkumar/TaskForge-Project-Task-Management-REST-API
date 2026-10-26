import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceRole
from app.models.project import Project
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.repositories.task_repository import TaskRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    InvalidStatusTransitionException,
)
from app.workers.notifications import dispatch_task_assignment_notification

# Allowed task state transitions
ALLOWED_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.COMPLETED},
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.TODO},
    TaskStatus.IN_REVIEW: {TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED},
    TaskStatus.BLOCKED: {TaskStatus.TODO, TaskStatus.IN_PROGRESS},
    TaskStatus.COMPLETED: {TaskStatus.IN_PROGRESS, TaskStatus.TODO},  # Reopening
}


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def create_task(self, task_in: TaskCreate, current_user: User) -> TaskResponse:
        project = self.project_repo.get_by_id(task_in.project_id)
        if not project:
            raise NotFoundException("Project", task_in.project_id)

        is_admin = current_user.role == UserRole.ADMIN
        if not self.project_repo.user_has_access(project.id, current_user.id, is_admin=is_admin):
            raise ForbiddenException("You do not have access to this project")

        # Validate assignee if provided
        if task_in.assignee_id:
            assignee = self.user_repo.get_by_id(task_in.assignee_id)
            if not assignee:
                raise NotFoundException("Assignee user", task_in.assignee_id)
            # Ensure assignee belongs to workspace
            assignee_role = self.workspace_repo.get_user_role(project.workspace_id, assignee.id)
            if not assignee_role and assignee.role != UserRole.ADMIN:
                raise BadRequestException("Assignee must be a member of the project workspace")

        # Validate deadline
        if task_in.due_date:
            now = datetime.now(timezone.utc)
            due_utc = task_in.due_date if task_in.due_date.tzinfo else task_in.due_date.replace(tzinfo=timezone.utc)
            if due_utc < now:
                raise BadRequestException("Task deadline cannot be in the past")

        task = Task(
            project_id=task_in.project_id,
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            status=task_in.status,
            due_date=task_in.due_date,
            assignee_id=task_in.assignee_id,
            created_by_id=current_user.id,
        )
        task = self.task_repo.create(task)

        # Audit log
        self.audit_repo.log(
            action="CREATE",
            entity_type="task",
            entity_id=task.id,
            actor_id=current_user.id,
            changes={"title": task.title, "project_id": task.project_id},
        )

        # Asynchronous notification
        if task.assignee_id:
            dispatch_task_assignment_notification(
                task_id=task.id,
                task_title=task.title,
                assignee_id=task.assignee_id,
                assigner_name=current_user.full_name or current_user.email,
            )

        return self._to_response(task)

    def get_task(self, task_id: int, current_user: User) -> TaskResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task", task_id)

        is_admin = current_user.role == UserRole.ADMIN
        if not self.project_repo.user_has_access(task.project_id, current_user.id, is_admin=is_admin):
            raise ForbiddenException("You do not have access to this task")

        return self._to_response(task)

    def update_task(
        self,
        task_id: int,
        task_in: TaskUpdate,
        current_user: User,
    ) -> TaskResponse:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task", task_id)

        project = self.project_repo.get_by_id(task.project_id)
        if not project:
            raise NotFoundException("Project", task.project_id)

        is_admin = current_user.role == UserRole.ADMIN
        if not self.project_repo.user_has_access(task.project_id, current_user.id, is_admin=is_admin):
            raise ForbiddenException("You do not have access to this task")

        changes = {}

        # Validate status transition
        if task_in.status is not None and task_in.status != task.status:
            allowed = ALLOWED_TRANSITIONS.get(task.status, set())
            if task_in.status not in allowed and not is_admin:
                raise InvalidStatusTransitionException(task.status.value, task_in.status.value)
            changes["status"] = {"old": task.status.value, "new": task_in.status.value}
            task.status = task_in.status

        # Validate deadline
        if task_in.due_date is not None and task_in.due_date != task.due_date:
            now = datetime.now(timezone.utc)
            due_utc = task_in.due_date if task_in.due_date.tzinfo else task_in.due_date.replace(tzinfo=timezone.utc)
            if due_utc < now and task.status != TaskStatus.COMPLETED:
                raise BadRequestException("Task deadline cannot be set to a past time")
            changes["due_date"] = {"old": str(task.due_date), "new": str(task_in.due_date)}
            task.due_date = task_in.due_date

        if task_in.title is not None and task_in.title != task.title:
            changes["title"] = {"old": task.title, "new": task_in.title}
            task.title = task_in.title

        if task_in.description is not None and task_in.description != task.description:
            changes["description"] = {"old": task.description, "new": task_in.description}
            task.description = task_in.description

        if task_in.priority is not None and task_in.priority != task.priority:
            changes["priority"] = {"old": task.priority.value, "new": task_in.priority.value}
            task.priority = task_in.priority

        # Assignee update & validation
        assignee_changed = False
        if task_in.assignee_id is not None and task_in.assignee_id != task.assignee_id:
            assignee = self.user_repo.get_by_id(task_in.assignee_id)
            if not assignee:
                raise NotFoundException("Assignee user", task_in.assignee_id)
            assignee_role = self.workspace_repo.get_user_role(project.workspace_id, assignee.id)
            if not assignee_role and assignee.role != UserRole.ADMIN:
                raise BadRequestException("Assignee must be a member of the project workspace")
            changes["assignee_id"] = {"old": task.assignee_id, "new": task_in.assignee_id}
            task.assignee_id = task_in.assignee_id
            assignee_changed = True

        task = self.task_repo.update(task)

        if changes:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="task",
                entity_id=task.id,
                actor_id=current_user.id,
                changes=changes,
            )

        if assignee_changed and task.assignee_id:
            dispatch_task_assignment_notification(
                task_id=task.id,
                task_title=task.title,
                assignee_id=task.assignee_id,
                assigner_name=current_user.full_name or current_user.email,
            )

        return self._to_response(task)

    def delete_task(self, task_id: int, current_user: User) -> None:
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("Task", task_id)

        project = self.project_repo.get_by_id(task.project_id)
        if not project:
            raise NotFoundException("Project", task.project_id)

        role = self.workspace_repo.get_user_role(project.workspace_id, current_user.id)
        is_creator = task.created_by_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN

        if not is_admin and not is_creator and role not in (
            WorkspaceRole.ADMIN,
            WorkspaceRole.PROJECT_MANAGER,
        ):
            raise ForbiddenException("You do not have permission to delete this task")

        self.audit_repo.log(
            action="DELETE",
            entity_type="task",
            entity_id=task.id,
            actor_id=current_user.id,
            changes={"title": task.title},
        )
        self.task_repo.delete(task)

    def filter_tasks(
        self,
        current_user: User,
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
        page: int = 1,
        page_size: int = 20,
    ) -> TaskListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        skip = (page - 1) * page_size
        is_admin = current_user.role == UserRole.ADMIN

        items, total = self.task_repo.filter_and_paginate(
            user_id=current_user.id,
            is_admin=is_admin,
            project_id=project_id,
            workspace_id=workspace_id,
            assignee_id=assignee_id,
            status=status,
            priority=priority,
            due_date_before=due_date_before,
            due_date_after=due_date_after,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        responses = [self._to_response(t) for t in items]

        return TaskListResponse(
            items=responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def _to_response(self, task: Task) -> TaskResponse:
        res = TaskResponse.model_validate(task)
        if task.due_date and task.status != TaskStatus.COMPLETED:
            now = datetime.now(timezone.utc)
            due_utc = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
            res.is_overdue = due_utc < now
        else:
            res.is_overdue = False
        return res
