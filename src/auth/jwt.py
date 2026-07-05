from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
import jwt

from core.config import settings


class TokenPayload(BaseModel):
    sub: str  # user_id as string
    is_guest: bool = False
    exp: datetime
    iat: datetime
    type: str = "access"  # "access" or "refresh"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(
    user_id: UUID,
    is_guest: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token for a user."""
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    elif is_guest:
        expire = now + timedelta(days=settings.guest_token_expire_days)
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": str(user_id),
        "is_guest": is_guest,
        "exp": expire,
        "iat": now,
        "type": "access"
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def create_guest_token(user_id: UUID) -> str:
    """Create a long-lived token specifically for guest users."""
    return create_access_token(
        user_id=user_id,
        is_guest=True,
        expires_delta=timedelta(days=settings.guest_token_expire_days)
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create a refresh token for token renewal."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "refresh"
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_expiry_seconds(is_guest: bool = False) -> int:
    """Get token expiry in seconds for response."""
    if is_guest:
        return settings.guest_token_expire_days * 24 * 60 * 60
    return settings.access_token_expire_minutes * 60
