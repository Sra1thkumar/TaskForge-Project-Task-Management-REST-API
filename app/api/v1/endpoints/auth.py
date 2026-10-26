from typing import Optional
from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.models.user import User
from app.api.deps import get_auth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new account, auto-generate personal workspace, and return access/refresh tokens.",
)
def register(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.register(user_in)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticate with email & password to retrieve access and refresh tokens.",
)
def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.login(login_data)


@router.post(
    "/login/oauth",
    response_model=TokenResponse,
    include_in_schema=True,
    summary="OAuth2 Form Login",
    description="OAuth2 form-encoded login endpoint for Swagger UI Authorize button.",
)
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    # form_data.username represents the user's email
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    return auth_service.login(login_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="Submit a valid refresh token to obtain a refreshed access token.",
)
def refresh_token(
    refresh_in: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return auth_service.refresh(refresh_in.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Fetch the authenticated user's profile and active roles.",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)
