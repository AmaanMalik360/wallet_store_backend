from fastapi import APIRouter, status, HTTPException, Query, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID

from src.models.db import DbSession
from . import models
from . import service
from src.middleware.image_upload import ImageUploadMiddleware

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

# Initialize image upload middleware for products
image_upload = ImageUploadMiddleware("public/images/products")

@router.post("/", response_model=models.ProductResponse, status_code=status.HTTP_201_CREATED)
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
        
        return service.create_product(db, product_data, image_paths)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create product")

@router.get("/", response_model=List[models.ProductResponse])
def get_products(
    db: DbSession,
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price in cents"),
    max_price: Optional[int] = Query(None, ge=0, description="Maximum price in cents"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    search: Optional[str] = Query(None, min_length=1, description="Search query to filter products by title or description")
):
    """
    Get products with optional filtering and search:
    - Pagination: skip and limit
    - Category filter: category_id
    - Price range: min_price and max_price
    - Stock filter: in_stock (True for in stock, False for out of stock)
    - Search: search query to filter by title or description
    """
    return service.get_products(
        db, 
        skip=skip, 
        limit=limit, 
        category_id=category_id,
        category_slug=category_slug,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        search=search
    )

@router.get("/{product_id}", response_model=models.ProductWithCategory)
def get_product(product_id: UUID, db: DbSession):
    """Get a specific product by ID with category information"""
    return service.get_product_by_id(db, product_id)

@router.put("/{product_id}", response_model=models.ProductResponse)
def update_product(
    product_id: UUID, 
    product_update: models.ProductUpdate, 
    db: DbSession
):
    """Update a product"""
    return service.update_product(db, product_id, product_update)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, db: DbSession):
    """Delete a product"""
    service.delete_product(db, product_id)
