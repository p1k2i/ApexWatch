"""
Dashboard Service Configuration
"""
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from typing import Tuple, Type
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent / ".env"),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='allow'
    )
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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # .env file overrides environment variables
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)


settings = Settings()
