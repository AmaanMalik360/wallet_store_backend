from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from pwdlib import PasswordHash

from . import models
from src.models.user import User
from src.models.cart import Cart
from src.auth.jwt import create_access_token, create_guest_token, create_refresh_token, get_token_expiry_seconds
from core.config import settings

logger = logging.getLogger(__name__)
password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def create_user(db: Session, user: models.UserCreate) -> User:
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = get_password_hash(user.password)
        
        # Create new user
        db_user = User(
            email=user.email,
            password=hashed_password,
            name=user.name,
            is_guest=user.is_guest
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"Created new user with email: {user.email}")
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user with email {user.email}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(users)} users")
    return users


def get_user_by_id(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Retrieved user {user_id}")
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    return user


def update_user(db: Session, user_id: UUID, user_update: models.UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Handle password update separately if provided
    if "password" in update_data:
        update_data["password"] = get_password_hash(update_data["password"])
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user {user_id}")
    return user


def delete_user(db: Session, user_id: UUID) -> None:
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()
    logger.info(f"Deleted user {user_id}")


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not user.password or not verify_password(password, user.password):
        return None
    return user


def create_guest_user(db: Session) -> dict:
    """
    Create a guest user with an associated cart and JWT token.
    Returns dict with user and token info.
    """
    try:
        # Calculate expiry date for guest account
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.guest_token_expire_days)
        
        # Create guest user
        guest_user = User(
            is_guest=True,
            guest_expires_at=expires_at
        )
        db.add(guest_user)
        db.flush()  # Get the user ID before creating cart
        
        # Create cart for guest user
        cart = Cart(user_id=guest_user.id)
        db.add(cart)
        
        db.commit()
        db.refresh(guest_user)
        
        # Generate guest token
        access_token = create_guest_token(guest_user.id)
        expires_in = get_token_expiry_seconds(is_guest=True)
        
        logger.info(f"Created guest user: {guest_user.id}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": guest_user
        }
        
    except Exception as e:
        logger.error(f"Failed to create guest user. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create guest user")


def login_user(db: Session, email: str, password: str) -> dict:
    """
    Authenticate user and return JWT token.
    """
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(user.id, is_guest=False)
    refresh_token = create_refresh_token(user.id)
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user
    }


def convert_guest_to_user(
    db: Session, 
    guest_user: User, 
    registration: models.GuestToUserRequest
) -> dict:
    """
    Convert a guest user to a registered user, preserving their cart.
    """
    if not guest_user.is_guest:
        raise HTTPException(
            status_code=400,
            detail="User is already registered"
        )
    
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == registration.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Update guest user to registered user
    guest_user.email = registration.email
    guest_user.password = get_password_hash(registration.password)
    guest_user.name = registration.name
    guest_user.is_guest = False
    guest_user.guest_expires_at = None
    
    db.commit()
    db.refresh(guest_user)
    
    # Generate new tokens for registered user
    access_token = create_access_token(guest_user.id, is_guest=False)
    refresh_token = create_refresh_token(guest_user.id)
    
    logger.info(f"Converted guest {guest_user.id} to registered user: {registration.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": guest_user
    }
