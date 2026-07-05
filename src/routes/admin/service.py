from typing import List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from src.models.role import Role, RolePermission
from src.models.permission import Permission
from src.models.user_role import UserRole
from src.models.user import User
from . import models

logger = logging.getLogger(__name__)


def get_all_roles(db: Session) -> List[Role]:
    """Get all roles with their permissions."""
    roles = (
        db.query(Role)
        .options(
            joinedload(Role.role_permissions)
            .joinedload(RolePermission.permission)
        )
        .all()
    )
    return roles


def get_role_by_id(db: Session, role_id: int) -> Role:
    """Get a role by ID with its permissions."""
    role = (
        db.query(Role)
        .options(
            joinedload(Role.role_permissions)
            .joinedload(RolePermission.permission)
        )
        .filter(Role.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def create_role(db: Session, role_data: models.RoleCreate) -> Role:
    """Create a new role with permissions."""
    try:
        existing = db.query(Role).filter(Role.name == role_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Role name already exists")
        
        role = Role(name=role_data.name, description=role_data.description)
        db.add(role)
        db.flush()
        
        if role_data.permission_ids:
            for perm_id in role_data.permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=perm_id)
                db.add(rp)
        
        db.commit()
        db.refresh(role)
        
        logger.info(f"Created role: {role.name}")
        return get_role_by_id(db, role.id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create role. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create role")


def update_role(db: Session, role_id: int, role_data: models.RoleUpdate) -> Role:
    """Update a role and its permissions."""
    role = get_role_by_id(db, role_id)
    
    if role_data.name is not None:
        existing = db.query(Role).filter(Role.name == role_data.name, Role.id != role_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Role name already exists")
        role.name = role_data.name
    
    if role_data.description is not None:
        role.description = role_data.description
    
    if role_data.permission_ids is not None:
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for perm_id in role_data.permission_ids:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)
    
    db.commit()
    logger.info(f"Updated role: {role.name}")
    return get_role_by_id(db, role_id)


def delete_role(db: Session, role_id: int) -> None:
    """Delete a role."""
    role = get_role_by_id(db, role_id)
    
    if role.name in ('super_admin', 'admin'):
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    db.delete(role)
    db.commit()
    logger.info(f"Deleted role: {role.name}")


def get_all_permissions(db: Session) -> List[Permission]:
    """Get all available permissions."""
    return db.query(Permission).all()


def assign_role_to_user(db: Session, user_id: UUID, role_id: int) -> UserRole:
    """Assign a role to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_guest:
        raise HTTPException(status_code=400, detail="Cannot assign roles to guest users")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    
    logger.info(f"Assigned role {role.name} to user {user_id}")
    return user_role


def remove_role_from_user(db: Session, user_id: UUID, role_id: int) -> None:
    """Remove a role from a user."""
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    ).first()
    if not user_role:
        raise HTTPException(status_code=404, detail="User does not have this role")
    
    db.delete(user_role)
    db.commit()
    logger.info(f"Removed role {role_id} from user {user_id}")


def get_user_with_roles(db: Session, user_id: UUID) -> dict:
    """Get user details with their roles."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_roles = (
        db.query(UserRole)
        .options(
            joinedload(UserRole.role)
            .joinedload(Role.role_permissions)
            .joinedload(RolePermission.permission)
        )
        .filter(UserRole.user_id == user_id)
        .all()
    )
    
    roles = [ur.role for ur in user_roles]
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_guest": user.is_guest,
        "roles": roles
    }
