from fastapi import APIRouter, status, HTTPException, Query
from typing import List, Optional

from src.models.db import DbSession
from . import models
from . import service

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.post("/", response_model=models.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: models.CategoryCreate, db: DbSession):
    """Create a new category"""
    return service.create_category(db, category)


@router.get("/", response_model=List[models.CategoryResponse])
def get_categories(
    db: DbSession, 
    slug: Optional[str] = Query(None, description="Get specific category by slug with its children. If not provided, returns all parent categories with their children."),
    skip: int = Query(0, ge=0, description="Number of parent categories to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of parent categories to return")
):
    """
    Get categories:
    - If no slug provided: Returns paginated parent categories with their children recursively
    - If slug provided: Returns only that category with its children recursively (pagination ignored)
    """
    return service.get_categories(db, slug, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=models.CategoryResponse)
def get_category(category_id: int, db: DbSession):
    """Get a specific category by ID"""
    category = service.get_category_by_id(db, category_id)
    return service.build_category_hierarchy(category)


@router.put("/{category_id}", response_model=models.CategoryResponse)
def update_category(
    category_id: int, 
    category_update: models.CategoryUpdate, 
    db: DbSession
):
    """Update a category"""
    category = service.update_category(db, category_id, category_update)
    return service.build_category_hierarchy(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession):
    """Delete a category (only if it has no children)"""
    service.delete_category(db, category_id)
