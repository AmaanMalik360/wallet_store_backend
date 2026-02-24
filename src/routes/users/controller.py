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


@router.post("/", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: models.UserCreate, db:DbSession):
    return service.create_user(db, user)


@router.get("/", response_model=List[models.UserResponse])
def get_users(db: DbSession, skip: int = 0, limit: int = 100):
    return service.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=models.UserResponse)
def get_user(user_id: UUID, db: DbSession):
    return service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=models.UserResponse)
def update_user(
    user_id: UUID, 
    user_update: models.UserUpdate, 
    db: DbSession
):
    return service.update_user(db, user_id, user_update)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: DbSession):
    service.delete_user(db, user_id)


@router.get("/email/{email}", response_model=models.UserResponse)
def get_user_by_email(email: str, db: DbSession):
    user = service.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
