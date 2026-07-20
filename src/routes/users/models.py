from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from src.routes.models import ApiResponse


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_guest: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: Optional[str] = None
    name: Optional[str] = None
    is_guest: bool
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = []

    class Config:
        from_attributes = True


class GuestUserResponse(BaseModel):
    id: UUID
    is_guest: bool = True
    created_at: datetime
    guest_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    user: GuestUserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserResponse


class GuestToUserRequest(BaseModel):
    """Request to convert a guest user to a registered user."""
    email: EmailStr
    password: str
    name: Optional[str] = None


# Response wrapper types using shared ApiResponse
class UserResponseWrapper(ApiResponse[UserResponse]):
    pass


class UsersListResponseWrapper(ApiResponse[list[UserResponse]]):
    pass


class AuthTokenResponseWrapper(ApiResponse[AuthTokenResponse]):
    pass


class LoginResponseWrapper(ApiResponse[LoginResponse]):
    pass
