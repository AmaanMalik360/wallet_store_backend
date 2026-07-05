from fastapi import APIRouter, status, HTTPException, Depends
from typing import List
from uuid import UUID

from src.models.db import DbSession
from src.models.user import User
from src.auth.dependencies import get_current_user, CurrentUser
from . import models
from . import service

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


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
def create_guest_user(db: DbSession):
    """
    Create a guest user with a cart and return a JWT token.
    The token should be stored in frontend cookies.
    """
    result = service.create_guest_user(db)
    return models.AuthTokenResponseWrapper(
        success=True,
        message="Guest user created successfully",
        data=models.AuthTokenResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=models.GuestUserResponse.model_validate(result["user"])
        )
    )


@router.post("/login", response_model=models.LoginResponseWrapper)
def login(credentials: models.LoginRequest, db: DbSession):
    """
    Authenticate user with email and password, return JWT token.
    """
    result = service.login_user(db, credentials.email, credentials.password)
    return models.LoginResponseWrapper(
        success=True,
        message="Login successful",
        data=models.LoginResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=models.UserResponse.model_validate(result["user"])
        )
    )


@router.post("/register", response_model=models.LoginResponseWrapper, status_code=status.HTTP_201_CREATED)
def register_guest(
    registration: models.GuestToUserRequest,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Convert a guest user to a registered user.
    Preserves the guest's cart and other data.
    """
    result = service.convert_guest_to_user(db, current_user, registration)
    return models.LoginResponseWrapper(
        success=True,
        message="Registration successful",
        data=models.LoginResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=models.UserResponse.model_validate(result["user"])
        )
    )


@router.get("/me", response_model=models.UserResponseWrapper)
def get_current_user_info(current_user: CurrentUser):
    """Get the current authenticated user's information."""
    return models.UserResponseWrapper(
        success=True,
        message="User retrieved successfully",
        data=current_user
    )
