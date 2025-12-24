"""
Wallet Monitor Service Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "wallet-monitor"
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Security
    ACCESS_KEY: str = "apexwatch-secret-key-change-in-production"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apexwatch"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Blockchain Configuration
    ALCHEMY_API_KEY: Optional[str] = None
    ETHEREUM_RPC_URL: str = "https://eth-mainnet.g.alchemy.com/v2/"
    ETHEREUM_WSS_URL: Optional[str] = None

    # Monitoring Configuration
    POLL_INTERVAL_SECONDS: int = 30
    BLOCK_CONFIRMATION_COUNT: int = 12
    MAX_BLOCKS_PER_SCAN: int = 1000

    # Core Service
    CORE_SERVICE_URL: str = "http://core:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
