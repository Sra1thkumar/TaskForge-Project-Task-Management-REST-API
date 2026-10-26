from typing import List
from fastapi import APIRouter, Depends, status
from app.models.user import User
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
)
from app.services.workspace_service import WorkspaceService
from app.api.deps import get_workspace_service, get_current_user

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post(
    "/",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
)
def create_workspace(
    workspace_in: WorkspaceCreate,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.create_workspace(workspace_in, current_user)


@router.get(
    "/",
    response_model=List[WorkspaceResponse],
    summary="List Accessible Workspaces",
)
def list_workspaces(
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.list_user_workspaces(current_user)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get Workspace Details",
)
def get_workspace(
    workspace_id: int,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.get_workspace(workspace_id, current_user)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update Workspace",
)
def update_workspace(
    workspace_id: int,
    workspace_in: WorkspaceUpdate,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.update_workspace(workspace_id, workspace_in, current_user)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Workspace",
)
def delete_workspace(
    workspace_id: int,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    workspace_service.delete_workspace(workspace_id, current_user)
    return None


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add / Invite Member to Workspace",
)
def add_workspace_member(
    workspace_id: int,
    member_in: WorkspaceMemberCreate,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.add_member(workspace_id, member_in, current_user)


@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    summary="List Workspace Members",
)
def list_workspace_members(
    workspace_id: int,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    return workspace_service.list_members(workspace_id, current_user)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Member from Workspace",
)
def remove_workspace_member(
    workspace_id: int,
    user_id: int,
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    current_user: User = Depends(get_current_user),
):
    workspace_service.remove_member(workspace_id, user_id, current_user)
    return None
