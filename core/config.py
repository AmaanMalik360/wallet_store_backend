from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import cached_property


class Settings(BaseSettings):
    # Application Settings
    app_name: str = "FastAPI Application"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Database Settings
    db_hostname: str = "localhost"
    db_port: int = 5432
    db_name: str = "fastapi_db"
    db_username: str = "postgres"
    db_password: str = "password"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # JWT Settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Settings
    api_v1_prefix: str = "/api/v1"
    
    # CORS Settings
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: List[str] = ["*"]
    
    # Schema management
    auto_create_tables: bool = False
    
    # Configure model to load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
        extra="ignore",
    )
    
    @cached_property
    def database_url(self) -> str:
        return f"postgresql://{self.db_username}:{self.db_password}@{self.db_hostname}:{self.db_port}/{self.db_name}"
    
    @cached_property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_username}:{self.db_password}@{self.db_hostname}:{self.db_port}/{self.db_name}"


# Create settings instance
settings = Settings()