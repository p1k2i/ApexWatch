"""
Core Service Configuration
Manages environment variables and settings for the ApexWatch Core Service
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "core-service"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    ACCESS_KEY: str = "apexwatch-secret-key-change-in-production"

    # Database Connections
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apexwatch"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # ClickHouse Configuration
    CLICKHOUSE_HOST: str = "clickhouse"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DB: str = "apexwatch"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_QUEUE: str = "events_queue"

    # LLM Configuration (OpenAI-compatible API)
    OPENAI_API_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_MODEL: str = "gpt-4o-mini"
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 120

    # Context Management
    CONTEXT_STALENESS_HOURS: int = 1
    CONTEXT_MAX_SIZE_KB: int = 500

    # Elasticsearch Configuration (for logging)
    ELASTICSEARCH_HOST: str = "elasticsearch"
    ELASTICSEARCH_PORT: int = 9200

    # Service URLs
    WALLET_MONITOR_URL: str = "http://wallet-monitor:8001"
    EXCHANGE_MONITOR_URL: str = "http://exchange-monitor:8002"
    NEWS_MONITOR_URL: str = "http://news-monitor:8003"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
