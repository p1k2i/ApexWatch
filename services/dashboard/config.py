"""
Dashboard Service Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "dashboard"
    HOST: str = "0.0.0.0"
    PORT: int = 8501

    # Security
    ACCESS_KEY: str = "apexwatch-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "dashboard-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apexwatch"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Service URLs
    CORE_SERVICE_URL: str = "http://core:8000"
    WALLET_MONITOR_URL: str = "http://wallet-monitor:8001"
    EXCHANGE_MONITOR_URL: str = "http://exchange-monitor:8002"
    NEWS_MONITOR_URL: str = "http://news-monitor:8003"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
