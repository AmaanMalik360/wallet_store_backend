from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated, Generator, AsyncGenerator
import logging
from contextlib import asynccontextmanager
from core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self):
        self._engine = None
        self._session_factory = None
    
    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(
                settings.database_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                echo=settings.debug
            )
            logger.info("Database engine created successfully")
        return self._engine
    
    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._session_factory
    
    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info("✅ Database connection successful")
                return True
        except SQLAlchemyError as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            logger.error(f"   Connection URL: postgresql://{settings.db_username}:***@{settings.db_hostname}:{settings.db_port}/{settings.db_name}")
            logger.error("   Please check your database configuration and ensure PostgreSQL is running")
            return False
    
    def create_tables(self):
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created/verified successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def get_session(self) -> Generator:
        db = self.session_factory()
        try:
            yield db
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def close(self):
        if self._engine:
            self._engine.dispose()
            logger.info("Database engine disposed")


# Global database manager instance
db_manager = DatabaseManager()

# Dependency function for FastAPI
def get_db() -> Generator:
    yield from db_manager.get_session()
DbSession = Annotated[Session, Depends(get_db)]



