import os
import uuid
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from PIL import Image
import io # Import io for PIL validation
import logging
logger = logging.getLogger(__name__)

class ImageUploadMiddleware:
    """Reusable middleware for handling image uploads"""
    
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, upload_directory: str):
        """
        Initialize the image upload middleware
        
        Args:
            upload_directory: Relative path from project root (e.g., 'public/images/products')
        """
        self.upload_directory = upload_directory
        self.ensure_upload_directory()
    
    def ensure_upload_directory(self):
        """Create upload directory if it doesn't exist"""
        try:
            # Get absolute path from project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            abs_upload_dir = os.path.join(project_root, self.upload_directory)
            
            os.makedirs(abs_upload_dir, exist_ok=True)
            logger.info(f"Upload directory ensured: {abs_upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory {self.upload_directory}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize upload directory")
    
    def validate_image(self, file: UploadFile) -> bool:
        """Validate uploaded file is an acceptable image"""
        # Check file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        if hasattr(file, 'size') and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE / (1024*1024):.1f}MB"
            )
        
        return True
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename to prevent collisions"""
        file_extension = os.path.splitext(original_filename)[1].lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"
    
    async def save_image(self, file: UploadFile) -> str:
        """
        Save uploaded image and return URL path
        
        Args:
            file: UploadFile object from FastAPI
            
        Returns:
            str: URL path for frontend consumption (e.g., '/static/images/products/uuid.jpg')
        """
        try:
            # Validate image
            self.validate_image(file)
            
            # Generate unique filename
            unique_filename = self.generate_unique_filename(file.filename)
            
            # Get absolute paths
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            abs_upload_dir = os.path.join(project_root, self.upload_directory)
            abs_file_path = os.path.join(abs_upload_dir, unique_filename)
            
            # Save file
            content = await file.read()
            
            # Additional validation: try to open with PIL to ensure it's a valid image
            try:
                Image.open(io.BytesIO(content))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")
            
            with open(abs_file_path, "wb") as f:
                f.write(content)
            
            # Return URL path for frontend consumption
            # Remove 'public/' prefix and add '/static/' prefix
            relative_path = os.path.join(self.upload_directory, unique_filename).replace('\\', '/')
            url_path = relative_path.replace('public/', '/static/')
            logger.info(f"Image saved successfully: {relative_path}")
            
            return url_path
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save image {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save image")
    
    async def save_multiple_images(self, files: List[UploadFile]) -> List[str]:
        """
        Save multiple uploaded images and return list of URL paths
        
        Args:
            files: List of UploadFile objects from FastAPI
            
        Returns:
            List[str]: List of URL paths for frontend consumption
        """
        if not files:
            return []
        
        paths = []
        for file in files:
            path = await self.save_image(file)
            paths.append(path)
        
        return paths
    
    def delete_image(self, relative_path: str) -> bool:
        """
        Delete an image file
        
        Args:
            relative_path: Relative path from project root
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            abs_file_path = os.path.join(project_root, relative_path)
            
            if os.path.exists(abs_file_path):
                os.remove(abs_file_path)
                logger.info(f"Image deleted successfully: {relative_path}")
                return True
            else:
                logger.warning(f"Image file not found for deletion: {relative_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete image {relative_path}: {str(e)}")
            return False


