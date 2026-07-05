from typing import Optional, Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload

from src.models.db import get_db
from src.models.user import User
from src.models.user_role import UserRole
from src.models.role import RolePermission
from .jwt import decode_token, TokenPayload


security = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """Extract token from HttpOnly cookie first, then Authorization header."""
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    if credentials:
        return credentials.credentials
    return None


async def get_optional_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Use this for routes that work with or without authentication.
    """
    token = _extract_token(request, credentials)
    if not token:
        return None
    
    token_data = decode_token(token)
    if not token_data or token_data.type != "access":
        return None
    
    user = db.query(User).filter(User.id == UUID(token_data.sub)).first()
    return user


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user (includes guests).
    Raises 401 if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = _extract_token(request, credentials)
    if not token:
        raise credentials_exception
    
    token_data = decode_token(token)
    if not token_data or token_data.type != "access":
        raise credentials_exception
    
    user = db.query(User).filter(User.id == UUID(token_data.sub)).first()
    if not user:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user, excluding guests.
    Use this for routes that require a registered (non-guest) user.
    """
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest users cannot access this resource"
        )
    return current_user


def get_user_permissions(db: Session, user_id: UUID) -> set[str]:
    """
    Get all permissions for a user by traversing their roles.
    Returns a set of permission names like {'products:create', 'orders:read'}
    """
    results = (
        db.query(RolePermission)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .options(joinedload(RolePermission.permission))
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return {rp.permission.name for rp in results}


def require_permission(permission: str):
    """
    Factory that returns a dependency checking for a specific permission.
    Used for RBAC-protected admin routes.
    
    Usage:
        @router.post("/products")
        def create_product(
            ...,
            _: User = Depends(require_permission("products:create"))
        ):
    """
    async def checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = get_user_permissions(db, current_user.id)
        
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required"
            )
        return current_user
    
    return checker


def require_any_permission(*permissions: str):
    """
    Factory that checks if user has ANY of the specified permissions.
    
    Usage:
        @router.get("/admin")
        def admin_dashboard(
            _: User = Depends(require_any_permission("admin:access", "super_admin"))
        ):
    """
    async def checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_permissions = get_user_permissions(db, current_user.id)
        
        if not user_permissions.intersection(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: one of {permissions} required"
            )
        return current_user
    
    return checker


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
