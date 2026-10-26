from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException, NotFoundException


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.workspace_repo = WorkspaceRepository(db)

    def register(self, user_in: UserCreate) -> TokenResponse:
        existing = self.user_repo.get_by_email(user_in.email)
        if existing:
            raise ConflictException(f"User with email '{user_in.email}' already exists")

        # Create user
        user = User(
            email=user_in.email.lower().strip(),
            full_name=user_in.full_name,
            password_hash=hash_password(user_in.password),
            role=user_in.role or UserRole.MEMBER,
            is_active=True,
        )
        user = self.user_repo.create(user)

        # Automatically create default workspace for the new user
        default_workspace = Workspace(
            name=f"{user.full_name or 'My'} Workspace",
            description="Default workspace created upon registration",
            owner_id=user.id,
        )
        self.workspace_repo.create(default_workspace)

        # Generate tokens
        return self._generate_tokens(user)

    def login(self, login_data: UserLogin) -> TokenResponse:
        user = self.user_repo.get_by_email(login_data.email.lower().strip())
        if not user or not verify_password(login_data.password, user.password_hash):
            raise UnauthorizedException("Incorrect email or password")

        if not user.is_active:
            raise UnauthorizedException("User account is inactive")

        return self._generate_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as e:
            raise UnauthorizedException(f"Invalid refresh token: {str(e)}")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type. Expected refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token payload missing subject")

        user = self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        return self._generate_tokens(user)

    def get_current_user_profile(self, user_id: int) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", user_id)
        return UserResponse.model_validate(user)

    def _generate_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )
