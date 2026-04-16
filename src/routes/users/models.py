from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.routes.models import ApiResponse


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    is_guest: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_guest: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Response wrapper types using shared ApiResponse
class UserResponseWrapper(ApiResponse[UserResponse]):
    pass


class UsersListResponseWrapper(ApiResponse[list[UserResponse]]):
    pass
