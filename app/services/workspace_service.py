from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
)
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    BadRequestException,
)


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.workspace_repo = WorkspaceRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def create_workspace(self, workspace_in: WorkspaceCreate, current_user: User) -> WorkspaceResponse:
        workspace = Workspace(
            name=workspace_in.name,
            description=workspace_in.description,
            owner_id=current_user.id,
        )
        workspace = self.workspace_repo.create(workspace)

        self.audit_repo.log(
            action="CREATE",
            entity_type="workspace",
            entity_id=workspace.id,
            actor_id=current_user.id,
            changes={"name": workspace.name},
        )
        return self._to_response(workspace)

    def get_workspace(self, workspace_id: int, current_user: User) -> WorkspaceResponse:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        # Check access
        role = self.workspace_repo.get_user_role(workspace_id, current_user.id)
        if not role and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have access to this workspace")

        return self._to_response(workspace)

    def list_user_workspaces(self, current_user: User) -> List[WorkspaceResponse]:
        is_admin = current_user.role == UserRole.ADMIN
        workspaces = self.workspace_repo.list_for_user(current_user.id, is_admin=is_admin)
        return [self._to_response(w) for w in workspaces]

    def update_workspace(
        self,
        workspace_id: int,
        workspace_in: WorkspaceUpdate,
        current_user: User,
    ) -> WorkspaceResponse:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        # Only workspace admin or owner or system admin can update
        role = self.workspace_repo.get_user_role(workspace_id, current_user.id)
        if role != WorkspaceRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("Only workspace administrators can edit this workspace")

        changes = {}
        if workspace_in.name is not None and workspace_in.name != workspace.name:
            changes["name"] = {"old": workspace.name, "new": workspace_in.name}
            workspace.name = workspace_in.name
        if workspace_in.description is not None and workspace_in.description != workspace.description:
            changes["description"] = {"old": workspace.description, "new": workspace_in.description}
            workspace.description = workspace_in.description

        workspace = self.workspace_repo.update(workspace)

        if changes:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="workspace",
                entity_id=workspace.id,
                actor_id=current_user.id,
                changes=changes,
            )

        return self._to_response(workspace)

    def delete_workspace(self, workspace_id: int, current_user: User) -> None:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        if workspace.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("Only the workspace owner can delete this workspace")

        self.audit_repo.log(
            action="DELETE",
            entity_type="workspace",
            entity_id=workspace.id,
            actor_id=current_user.id,
            changes={"name": workspace.name},
        )
        self.workspace_repo.delete(workspace)

    def add_member(
        self,
        workspace_id: int,
        member_in: WorkspaceMemberCreate,
        current_user: User,
    ) -> WorkspaceMemberResponse:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        # Only workspace admin or system admin can invite
        role = self.workspace_repo.get_user_role(workspace_id, current_user.id)
        if role != WorkspaceRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("Only workspace administrators can add members")

        target_user = self.user_repo.get_by_email(member_in.user_email.lower().strip())
        if not target_user:
            raise NotFoundException(f"User with email '{member_in.user_email}'")

        existing_member = self.workspace_repo.get_member(workspace_id, target_user.id)
        if existing_member:
            raise ConflictException("User is already a member of this workspace")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role=member_in.role,
        )
        member = self.workspace_repo.add_member(member)

        self.audit_repo.log(
            action="ADD_MEMBER",
            entity_type="workspace",
            entity_id=workspace_id,
            actor_id=current_user.id,
            changes={"added_user_id": target_user.id, "role": member_in.role.value},
        )
        return WorkspaceMemberResponse.model_validate(member)

    def remove_member(
        self,
        workspace_id: int,
        target_user_id: int,
        current_user: User,
    ) -> None:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        if workspace.owner_id == target_user_id:
            raise BadRequestException("Cannot remove the owner of the workspace")

        role = self.workspace_repo.get_user_role(workspace_id, current_user.id)
        if role != WorkspaceRole.ADMIN and current_user.id != target_user_id and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to remove this member")

        member = self.workspace_repo.get_member(workspace_id, target_user_id)
        if not member:
            raise NotFoundException("Workspace member not found")

        self.workspace_repo.remove_member(member)
        self.audit_repo.log(
            action="REMOVE_MEMBER",
            entity_type="workspace",
            entity_id=workspace_id,
            actor_id=current_user.id,
            changes={"removed_user_id": target_user_id},
        )

    def list_members(self, workspace_id: int, current_user: User) -> List[WorkspaceMemberResponse]:
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise NotFoundException("Workspace", workspace_id)

        role = self.workspace_repo.get_user_role(workspace_id, current_user.id)
        if not role and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have access to this workspace")

        members = self.workspace_repo.list_members(workspace_id)
        return [WorkspaceMemberResponse.model_validate(m) for m in members]

    def _to_response(self, workspace: Workspace) -> WorkspaceResponse:
        res = WorkspaceResponse.model_validate(workspace)
        res.members_count = self.workspace_repo.count_members(workspace.id)
        res.projects_count = self.workspace_repo.count_projects(workspace.id)
        return res
