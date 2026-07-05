from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.routes.models import ApiResponse


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: list[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[int]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: list[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    user_id: UUID
    role_id: int


class UserRoleResponse(BaseModel):
    user_id: UUID
    role_id: int
    role_name: str
    assigned_at: datetime

    class Config:
        from_attributes = True


class UserWithRolesResponse(BaseModel):
    id: UUID
    email: Optional[str] = None
    name: Optional[str] = None
    is_guest: bool
    roles: list[RoleResponse] = []

    class Config:
        from_attributes = True


# Response wrappers
class RoleResponseWrapper(ApiResponse[RoleResponse]):
    pass


class RolesListResponseWrapper(ApiResponse[list[RoleResponse]]):
    pass


class PermissionsListResponseWrapper(ApiResponse[list[PermissionResponse]]):
    pass


class UserWithRolesResponseWrapper(ApiResponse[UserWithRolesResponse]):
    pass
