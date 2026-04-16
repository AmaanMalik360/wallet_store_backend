from fastapi import APIRouter, status, HTTPException
from typing import List
from uuid import UUID

from src.models.db import DbSession
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
