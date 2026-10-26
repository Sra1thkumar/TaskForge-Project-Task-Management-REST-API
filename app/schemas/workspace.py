from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.workspace import WorkspaceRole
from app.schemas.user import UserResponse


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceMemberCreate(BaseModel):
    user_email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: WorkspaceRole
    user: Optional[UserResponse] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponse(WorkspaceBase):
    id: int
    owner_id: int
    owner: Optional[UserResponse] = None
    members_count: Optional[int] = 0
    projects_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
