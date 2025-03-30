"""Configuration settings for Whitelist Hub."""

import os
import secrets
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, validator


class Settings(BaseSettings):
    """Application settings."""

    # Base settings
    PROJECT_NAME: str = "Whitelist Hub"
    PROJECT_DESCRIPTION: str = "Blockchain project analysis platform focusing on whitelist mechanisms"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "whitelist_hub"
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # AI model settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    CUSTOM_AI_KEY: Optional[str] = None
    CUSTOM_AI_ENDPOINT: Optional[str] = None
    AI_MODEL_PROVIDER: str = "openai"  # or "anthropic", "gemini", "custom"
    
    # External service API keys and endpoints
    FIRECRAWL_API_KEY: Optional[str] = None
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Blockchain settings
    ETHEREUM_RPC_URL: Optional[str] = None
    BSC_RPC_URL: Optional[str] = None
    POLYGON_RPC_URL: Optional[str] = None
    ARBITRUM_RPC_URL: Optional[str] = None
    OPTIMISM_RPC_URL: Optional[str] = None
    
    # Blockchain explorer API keys
    ETHERSCAN_API_KEY: Optional[str] = None
    BSCSCAN_API_KEY: Optional[str] = None
    POLYGONSCAN_API_KEY: Optional[str] = None
    ARBISCAN_API_KEY: Optional[str] = None
    OPTIMISTICSCAN_API_KEY: Optional[str] = None
    
    # Security settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Crawler settings
    CRAWLER_USER_AGENT: str = "WhitelistHub/0.1.0 (+https://whitelisthub.io/bot)"
    
    class Config:
        """Pydantic config."""
        
        case_sensitive = True
        env_file = ".env"


settings = Settings()
