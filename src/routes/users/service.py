from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from pwdlib import PasswordHash  # New import
from pwdlib.hashers.argon2 import Argon2Hasher  # Optional, for explicit algo
from pwdlib.hashers.bcrypt import BcryptHasher  # Optional, if sticking with Bcrypt

from . import models
from src.models.user import User

logger = logging.getLogger(__name__)
password_hash = PasswordHash.recommended()  # Or PasswordHash(BcryptHasher()) for Bcrypt

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
        password_hash = get_password_hash(user.password)
        
        # Create new user
        db_user = User(
            email=user.email,
            password_hash=password_hash,
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
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
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
    if not verify_password(password, user.password_hash):
        return None
    return user
