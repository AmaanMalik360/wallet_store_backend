from fastapi import APIRouter, status, HTTPException, Query
from typing import List, Optional

from src.models.db import DbSession
from . import models
from . import service
from src.routes.attributes.service import (
    get_attributes_for_category,
    assign_attributes_to_category
)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.post("/", response_model=models.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: models.CategoryCreate, db: DbSession):
    """Create a new category"""
    category_data = service.create_category(db, category)
    return models.CategoryResponse(
        success=True,
        message="Category created successfully",
        data=category_data
    )


@router.get("/", response_model=models.CategoriesListResponse)
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
    categories_data = service.get_categories(db, slug, skip=skip, limit=limit)
    return models.CategoriesListResponse(
        success=True,
        message="Categories retrieved successfully",
        data=categories_data
    )


@router.get("/{category_id}", response_model=models.CategoryResponse)
def get_category(category_id: int, db: DbSession):
    """Get a specific category by ID"""
    category = service.get_category_by_id(db, category_id)
    category_data = service.build_category_hierarchy(category)
    return models.CategoryResponse(
        success=True,
        message="Category retrieved successfully",
        data=category_data
    )


@router.put("/{category_id}", response_model=models.CategoryResponse)
def update_category(
    category_id: int, 
    category_update: models.CategoryUpdate, 
    db: DbSession
):
    """Update a category"""
    category_data = service.update_category(db, category_id, category_update)
    return models.CategoryResponse(
        success=True,
        message="Category updated successfully",
        data=category_data
    )


@router.delete("/{category_id}", response_model=models.ApiResponse)
def delete_category(category_id: int, db: DbSession):
    """Delete a category (only if it has no children)"""
    service.delete_category(db, category_id)
    return models.ApiResponse(
        success=True,
        message="Category deleted successfully",
        data=None
    )


@router.get("/{category_id}/attributes", response_model=models.ApiResponse)
def get_category_attributes(category_id: int, db: DbSession):
    """Get filterable attributes and their values for a given category ID"""
    attributes = get_attributes_for_category(db, category_id)
    return models.ApiResponse(
        success=True,
        message="Attributes retrieved successfully",
        data={"attributes": attributes}
    )


@router.post("/{category_id}/attributes", response_model=models.ApiResponse)
def assign_attributes_to_category_endpoint(
    category_id: int,
    request: dict,
    db: DbSession
):
    """
    Assign a list of attributes to a category.
    Replaces existing assignments — sends the full desired list each time.
    
    Request body: {"attribute_ids": [1, 2, 3]}
    """
    attribute_ids = request.get("attribute_ids", [])
    assignments = assign_attributes_to_category(db, category_id, attribute_ids)
    return models.ApiResponse(
        success=True,
        message="Attributes assigned to category successfully",
        data={
            "category_id": category_id,
            "attribute_ids": [a.attribute_id for a in assignments]
        }
    )
