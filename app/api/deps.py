from typing import Generator, Optional, Callable
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.report_service import ReportService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise UnauthorizedException(f"Invalid authentication token: {str(e)}")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type. Expected access token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token payload missing subject")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    if not user:
        raise UnauthorizedException("User associated with token not found")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive")

    return user


def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Administrator privileges required")
    return current_user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.ADMIN:
            raise ForbiddenException(
                f"Action requires one of the following roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker


# Service factory dependencies
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db)


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)
