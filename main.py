from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from src.api import register_routes
from src.models.db import db_manager, get_db
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting FastAPI application...")
    
    # Test database connection
    if not db_manager.test_connection():
        logger.error("❌ Database connection failed during startup")
        raise Exception("Database connection failed")
    
    # Create database tables (optional, controlled by settings)
    if settings.auto_create_tables:
        try:
            db_manager.create_tables()
            logger.info("✅ Application startup complete - Database connected and tables created")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {str(e)}")
            raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down FastAPI application...")
    db_manager.close()
    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="A modern FastAPI application with SQLAlchemy 2.0",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

register_routes(app)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health")
async def health_check(db=Depends(get_db)):
    try:
        # Test database connection
        db_status = "connected" if db_manager.test_connection() else "disconnected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "environment": settings.environment,
            "version": settings.app_version
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
