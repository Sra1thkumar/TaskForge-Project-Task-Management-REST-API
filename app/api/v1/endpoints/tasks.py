from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.models.user import User
from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
)
from app.services.task_service import TaskService
from app.api.deps import get_task_service, get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
    description="Create a task with priority, due date, status, and optional assignee.",
)
def create_task(
    task_in: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    return task_service.create_task(task_in, current_user)


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="Filter and Paginate Tasks",
    description="Advanced search, multi-field filtering (status, priority, assignee, due dates), and sorting.",
)
def list_tasks(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace ID"),
    assignee_id: Optional[int] = Query(None, description="Filter by assigned user ID"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    due_date_before: Optional[datetime] = Query(None, description="Filter tasks due before this timestamp"),
    due_date_after: Optional[datetime] = Query(None, description="Filter tasks due after this timestamp"),
    search: Optional[str] = Query(None, description="Search task title and description"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, due_date, priority, status)"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    return task_service.filter_tasks(
        current_user=current_user,
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
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get Task Details",
)
def get_task(
    task_id: int,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    return task_service.get_task(task_id, current_user)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update Task",
    description="Update task fields. Validates permitted status transitions and future deadlines.",
)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    return task_service.update_task(task_id, task_in, current_user)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Task",
)
def delete_task(
    task_id: int,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    task_service.delete_task(task_id, current_user)
    return None
