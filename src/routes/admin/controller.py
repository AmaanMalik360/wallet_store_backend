from fastapi import APIRouter, status, Depends
from uuid import UUID

from src.models.db import DbSession
from src.auth.dependencies import require_permission
from . import models
from . import service

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


# ========== ROLES ==========

@router.get("/roles", response_model=models.RolesListResponseWrapper)
def get_roles(
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Get all roles with their permissions."""
    roles = service.get_all_roles(db)
    role_responses = []
    for role in roles:
        permissions = [rp.permission for rp in role.role_permissions]
        role_responses.append(models.RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        ))
    return models.RolesListResponseWrapper(
        success=True,
        message="Roles retrieved successfully",
        data=role_responses
    )


@router.get("/roles/{role_id}", response_model=models.RoleResponseWrapper)
def get_role(
    role_id: int,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Get a specific role with its permissions."""
    role = service.get_role_by_id(db, role_id)
    permissions = [rp.permission for rp in role.role_permissions]
    return models.RoleResponseWrapper(
        success=True,
        message="Role retrieved successfully",
        data=models.RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
    )


@router.post("/roles", response_model=models.RoleResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: models.RoleCreate,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Create a new role."""
    role = service.create_role(db, role_data)
    permissions = [rp.permission for rp in role.role_permissions]
    return models.RoleResponseWrapper(
        success=True,
        message="Role created successfully",
        data=models.RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
    )


@router.put("/roles/{role_id}", response_model=models.RoleResponseWrapper)
def update_role(
    role_id: int,
    role_data: models.RoleUpdate,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Update a role."""
    role = service.update_role(db, role_id, role_data)
    permissions = [rp.permission for rp in role.role_permissions]
    return models.RoleResponseWrapper(
        success=True,
        message="Role updated successfully",
        data=models.RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Delete a role."""
    service.delete_role(db, role_id)


# ========== PERMISSIONS ==========

@router.get("/permissions", response_model=models.PermissionsListResponseWrapper)
def get_permissions(
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Get all available permissions."""
    permissions = service.get_all_permissions(db)
    return models.PermissionsListResponseWrapper(
        success=True,
        message="Permissions retrieved successfully",
        data=permissions
    )


# ========== USER ROLES ==========

@router.post("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_201_CREATED)
def assign_role(
    user_id: UUID,
    role_id: int,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Assign a role to a user."""
    service.assign_role_to_user(db, user_id, role_id)
    return {"success": True, "message": "Role assigned successfully"}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role(
    user_id: UUID,
    role_id: int,
    db: DbSession,
    _=Depends(require_permission("roles:manage"))
):
    """Remove a role from a user."""
    service.remove_role_from_user(db, user_id, role_id)


@router.get("/users/{user_id}/roles", response_model=models.UserWithRolesResponseWrapper)
def get_user_roles(
    user_id: UUID,
    db: DbSession,
    _=Depends(require_permission("users:read"))
):
    """Get a user's roles."""
    user_data = service.get_user_with_roles(db, user_id)
    
    role_responses = []
    for role in user_data["roles"]:
        permissions = [rp.permission for rp in role.role_permissions]
        role_responses.append(models.RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
            updated_at=role.updated_at
        ))
    
    return models.UserWithRolesResponseWrapper(
        success=True,
        message="User roles retrieved successfully",
        data=models.UserWithRolesResponse(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data["name"],
            is_guest=user_data["is_guest"],
            roles=role_responses
        )
    )
