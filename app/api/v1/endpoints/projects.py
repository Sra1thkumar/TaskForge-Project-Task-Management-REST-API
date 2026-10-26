from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.models.user import User
from app.models.project import ProjectStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.schemas.task import TaskCreate, TaskResponse
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.api.deps import get_project_service, get_task_service, get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
)
def create_project(
    project_in: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    return project_service.create_project(project_in, current_user)


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List Accessible Projects",
    description="Filter by workspace_id, status, search query, and paginate results.",
)
def list_projects(
    workspace_id: Optional[int] = Query(None, description="Filter by workspace"),
    status: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    return project_service.list_projects(
        current_user=current_user,
        workspace_id=workspace_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project Details",
    description="Retrieve project information along with calculated completion percentage.",
)
def get_project(
    project_id: int,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    return project_service.get_project(project_id, current_user)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project",
)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    return project_service.update_project(project_id, project_in, current_user)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
)
def delete_project(
    project_id: int,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    project_service.delete_project(project_id, current_user)
    return None


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Task Under Project",
    description="Convenient endpoint to directly create a task under this project.",
)
def create_project_task(
    project_id: int,
    task_in: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
):
    # Ensure project_id in route takes precedence
    task_in.project_id = project_id
    return task_service.create_task(task_in, current_user)
