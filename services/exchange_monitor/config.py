"""
Exchange Monitor Service Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "exchange-monitor"
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # Security
    ACCESS_KEY: str = "apexwatch-secret-key-change-in-production"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apexwatch"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Monitoring Configuration
    POLL_INTERVAL_SECONDS: int = 60
    PRICE_CHANGE_THRESHOLD: float = 5.0  # percentage
    VOLUME_SPIKE_THRESHOLD: float = 200.0  # percentage

    # Core Service
    CORE_SERVICE_URL: str = "http://core:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
