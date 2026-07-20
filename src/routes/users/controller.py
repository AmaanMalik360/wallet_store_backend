from fastapi import APIRouter, status, HTTPException, Depends, Request, Response
from typing import List
from uuid import UUID

from src.models.db import DbSession
from src.models.user import User
from src.auth.dependencies import get_current_user, CurrentUser, get_user_permissions
from src.auth.jwt import decode_token, create_access_token
from core.config import settings
from . import models
from . import service

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly auth cookies on the response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/users/refresh",
    )


def _set_guest_cookie(response: Response, access_token: str) -> None:
    """Set long-lived HttpOnly access cookie for guest users (no refresh token)."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.guest_token_expire_days * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies."""
    response.delete_cookie(key="access_token", samesite="lax")
    response.delete_cookie(key="refresh_token", samesite="lax", path="/api/v1/users/refresh")


def _user_response_with_permissions(db, user: User) -> models.UserResponse:
    """Build a UserResponse including the user's effective permissions."""
    response = models.UserResponse.model_validate(user)
    response.permissions = list(get_user_permissions(db, user.id))
    return response


@router.post("/", response_model=models.UserResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_user(user: models.UserCreate, db:DbSession):
    user_data = service.create_user(db, user)
    return models.UserResponseWrapper(
        success=True,
        message="User created successfully",
        data=user_data
    )


@router.get("/", response_model=models.UsersListResponseWrapper)
def get_users(db: DbSession, skip: int = 0, limit: int = 100):
    users = service.get_users(db, skip=skip, limit=limit)
    return models.UsersListResponseWrapper(
        success=True,
        message="Users retrieved successfully",
        data=users
    )


@router.get("/{user_id}", response_model=models.UserResponseWrapper)
def get_user(user_id: UUID, db: DbSession):
    user = service.get_user_by_id(db, user_id)
    return models.UserResponseWrapper(
        success=True,
        message="User retrieved successfully",
        data=user
    )


@router.put("/{user_id}", response_model=models.UserResponseWrapper)
def update_user(
    user_id: UUID,
    user_update: models.UserUpdate,
    db: DbSession
):
    user = service.update_user(db, user_id, user_update)
    return models.UserResponseWrapper(
        success=True,
        message="User updated successfully",
        data=user
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: DbSession):
    service.delete_user(db, user_id)


@router.get("/email/{email}", response_model=models.UserResponseWrapper)
def get_user_by_email(email: str, db: DbSession):
    user = service.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return models.UserResponseWrapper(
        success=True,
        message="User retrieved successfully",
        data=user
    )


@router.post("/guest", response_model=models.AuthTokenResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_guest_user(response: Response, db: DbSession):
    """
    Create a guest user with a cart. Sets a long-lived access_token HttpOnly cookie.
    """
    result = service.create_guest_user(db)
    _set_guest_cookie(response, result["access_token"])
    return models.AuthTokenResponseWrapper(
        success=True,
        message="Guest user created successfully",
        data=models.AuthTokenResponse(
            user=models.GuestUserResponse.model_validate(result["user"])
        )
    )


@router.post("/login", response_model=models.LoginResponseWrapper)
def login(credentials: models.LoginRequest, response: Response, db: DbSession):
    """
    Authenticate user with email and password.
    Sets access_token and refresh_token as HttpOnly cookies.
    """
    result = service.login_user(db, credentials.email, credentials.password)
    _set_auth_cookies(response, result["access_token"], result["refresh_token"])
    return models.LoginResponseWrapper(
        success=True,
        message="Login successful",
        data=models.LoginResponse(
            user=_user_response_with_permissions(db, result["user"])
        )
    )


@router.post("/register", response_model=models.LoginResponseWrapper, status_code=status.HTTP_201_CREATED)
def register_guest(
    registration: models.GuestToUserRequest,
    response: Response,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Convert a guest user to a registered user.
    Preserves the guest's cart and other data.
    Sets new access_token and refresh_token HttpOnly cookies.
    """
    result = service.convert_guest_to_user(db, current_user, registration)
    _set_auth_cookies(response, result["access_token"], result["refresh_token"])
    return models.LoginResponseWrapper(
        success=True,
        message="Registration successful",
        data=models.LoginResponse(
            user=_user_response_with_permissions(db, result["user"])
        )
    )


@router.get("/me", response_model=models.UserResponseWrapper)
def get_current_user_info(current_user: CurrentUser, db: DbSession):
    """Get the current authenticated user's information."""
    return models.UserResponseWrapper(
        success=True,
        message="User retrieved successfully",
        data=_user_response_with_permissions(db, current_user)
    )


@router.post("/refresh", response_model=models.UserResponseWrapper)
def refresh_token(request: Request, response: Response, db: DbSession):
    """
    Use the refresh_token cookie to issue a new access_token cookie.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided"
        )

    token_data = decode_token(refresh_token_value)
    if not token_data or token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user = db.query(User).filter(User.id == UUID(token_data.sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    new_access_token = create_access_token(user.id, is_guest=user.is_guest)
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return models.UserResponseWrapper(
        success=True,
        message="Token refreshed",
        data=_user_response_with_permissions(db, user)
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """Clear auth cookies and log out the user."""
    _clear_auth_cookies(response)
