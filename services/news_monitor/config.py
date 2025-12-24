"""
News Monitor Service Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "news-monitor"
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    # Security
    ACCESS_KEY: str = "apexwatch-secret-key-change-in-production"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apexwatch"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Monitoring Configuration
    POLL_INTERVAL_SECONDS: int = 300  # 5 minutes
    MIN_RELEVANCE_SCORE: float = 0.3

    # Core Service
    CORE_SERVICE_URL: str = "http://core:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
