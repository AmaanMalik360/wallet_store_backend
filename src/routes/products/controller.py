from fastapi import APIRouter, status, HTTPException, Query, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID

from src.models.db import DbSession
from . import models
from . import service
from src.middleware.image_upload import ImageUploadMiddleware
import logging
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

# Initialize image upload middleware for products
image_upload = ImageUploadMiddleware("public/images/products")

@router.post("/", response_model=models.ProductResponseWrapper, status_code=status.HTTP_201_CREATED)
async def create_product(
    db: DbSession,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    price: int = Form(...),
    stock_quantity: int = Form(...),
    images: Optional[List[UploadFile]] = File(None, description="Product images")
):
    """
    Create a new product with optional image uploads

    Args:
        title: Product title
        description: Product description
        category_id: Category ID
        price: Price in cents
        stock_quantity: Number of items in stock
        images: Optional list of image files
    """
    try:
        # Handle image uploads
        image_paths = []
        if images:
            image_paths = await image_upload.save_multiple_images(images)

        # Create product data
        product_data = models.ProductCreate(
            title=title,
            description=description,
            category_id=category_id,
            price=price,
            stock_quantity=stock_quantity,
            images=image_paths
        )

        product = service.create_product(db, product_data, image_paths)
        return models.ProductResponseWrapper(
            success=True,
            message="Product created successfully",
            data=product
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create product")

@router.get("/", response_model=models.PaginatedProductsResponseWrapper)
def get_products(
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_ids: Optional[List[int]] = Query(None, description="Filter by multiple category IDs"),
    category_slug: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    in_stock: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=1),
    sort_by: Optional[str] = Query(None, description="featured | price-low | price-high | newest | name"),
    attribute_value_ids: Optional[List[int]] = Query(None, description="Filter by attribute value IDs")
):
    """
    Get products with optional filtering and search:
    - Pagination: skip and limit
    - Category filter: category_ids (multiple IDs) or category_slug
    - Price range: min_price and max_price
    - Stock filter: in_stock (True for in stock, False for out of stock)
    - Search: search query to filter by title or description
    - Sort: sort_by (featured, price-low, price-high, newest, name)
    - Attributes: attribute_value_ids (filter by attribute values)
    """
    products = service.get_products(
        db,
        skip=skip,
        limit=limit,
        category_ids=category_ids,
        category_slug=category_slug,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        search=search,
        sort_by=sort_by,
        attribute_value_ids=attribute_value_ids
    )
    return models.PaginatedProductsResponseWrapper(
        success=True,
        message="Products retrieved successfully",
        data=products
    )

@router.get("/{product_id}", response_model=models.ProductWithCategoryResponseWrapper)
def get_product(product_id: UUID, db: DbSession):
    """Get a specific product by ID with category information"""
    product = service.get_product_by_id(db, product_id)
    return models.ProductWithCategoryResponseWrapper(
        success=True,
        message="Product retrieved successfully",
        data=product
    )

@router.patch("/{product_id}", response_model=models.ProductResponseWrapper)
async def update_product(
    product_id: UUID,
    db: DbSession,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    price: Optional[int] = Form(None),
    stock_quantity: Optional[int] = Form(None),
    images: Optional[str] = Form(None, description="JSON string of existing image URLs"),
    new_images: Optional[List[UploadFile]] = File(None, description="New image files to upload")
):
    """
    Update a product with optional new image uploads

    Args:
        product_id: Product ID to update
        title: Product title
        description: Product description
        category_id: Category ID
        price: Price in cents
        stock_quantity: Number of items in stock
        images: JSON string of existing image URLs (or null)
        new_images: New image files to upload
    """
    try:
        import json

        # Build update data directly
        update_data = {}

        # Add text fields if provided
        if title is not None:
            update_data['title'] = title
        if description is not None:
            update_data['description'] = description
        if category_id is not None:
            update_data['category_id'] = category_id
        if price is not None:
            update_data['price'] = price
        if stock_quantity is not None:
            update_data['stock_quantity'] = stock_quantity

        # Handle image updates
        if images is not None or new_images:
            # Parse existing images from JSON string
            existing_images = []
            if images:
                try:
                    logger.info(f"Existing images: {images}")
                    existing_images = json.loads(images)
                    if existing_images is None:
                        existing_images = []
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid images JSON format")
            elif new_images:
                # If no existing images provided but new images are uploaded,
                # get current product images to preserve them
                current_product = service.get_product_by_id(db, product_id)
                existing_images = current_product.images or []

            # Handle new image uploads
            new_image_paths = []
            if new_images:
                new_image_paths = await image_upload.save_multiple_images(new_images)

            # Combine existing images with new image paths
            final_images = existing_images + new_image_paths if existing_images else new_image_paths
            update_data['images'] = final_images

        product = service.update_product(db, product_id, update_data)
        return models.ProductResponseWrapper(
            success=True,
            message="Product updated successfully",
            data=product
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update product")

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, db: DbSession):
    """Delete a product"""
    service.delete_product(db, product_id)
