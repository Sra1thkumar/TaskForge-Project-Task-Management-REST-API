from typing import Optional, List
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.project import Project


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, workspace_id: int) -> Optional[Workspace]:
        return self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        ).scalar_one_or_none()

    def create(self, workspace: Workspace) -> Workspace:
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        # Automatically add the owner as an Admin member of the workspace
        owner_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=workspace.owner_id,
            role=WorkspaceRole.ADMIN,
        )
        self.db.add(owner_member)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def update(self, workspace: Workspace) -> Workspace:
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def delete(self, workspace: Workspace) -> None:
        self.db.delete(workspace)
        self.db.commit()

    def list_for_user(self, user_id: int, is_admin: bool = False) -> List[Workspace]:
        if is_admin:
            return list(self.db.execute(select(Workspace)).scalars().all())
        
        # Select workspaces where user is owner or a member
        query = (
            select(Workspace)
            .outerjoin(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(or_(Workspace.owner_id == user_id, WorkspaceMember.user_id == user_id))
            .distinct()
        )
        return list(self.db.execute(query).scalars().all())

    def get_user_role(self, workspace_id: int, user_id: int) -> Optional[WorkspaceRole]:
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return None
        if workspace.owner_id == user_id:
            return WorkspaceRole.ADMIN

        member = self.get_member(workspace_id, user_id)
        return member.role if member else None

    def get_member(self, workspace_id: int, user_id: int) -> Optional[WorkspaceMember]:
        return self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        ).scalar_one_or_none()

    def add_member(self, member: WorkspaceMember) -> WorkspaceMember:
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, member: WorkspaceMember) -> None:
        self.db.delete(member)
        self.db.commit()

    def list_members(self, workspace_id: int) -> List[WorkspaceMember]:
        return list(
            self.db.execute(
                select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
            ).scalars().all()
        )

    def count_projects(self, workspace_id: int) -> int:
        return self.db.execute(
            select(func.count(Project.id)).where(Project.workspace_id == workspace_id)
        ).scalar_one()

    def count_members(self, workspace_id: int) -> int:
        return self.db.execute(
            select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace_id)
        ).scalar_one()
