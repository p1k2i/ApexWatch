"""
Database connection managers for PostgreSQL, Redis, and ClickHouse
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import clickhouse_connect
from contextlib import contextmanager
from config import settings
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages connections to PostgreSQL, Redis, and ClickHouse"""

    def __init__(self):
        self.pg_conn_params = {
            'host': settings.POSTGRES_HOST,
            'port': settings.POSTGRES_PORT,
            'database': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD
        }

        self.redis_client = None
        self.clickhouse_client = None

    def initialize(self):
        """Initialize all database connections"""
        try:
            # Test PostgreSQL connection
            with self.get_pg_connection() as conn:
                logger.info("PostgreSQL connection successful")

            # Initialize Redis
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection successful")

            # Initialize ClickHouse
            self.clickhouse_client = clickhouse_connect.get_client(
                host=settings.CLICKHOUSE_HOST,
                port=settings.CLICKHOUSE_PORT,
                database=settings.CLICKHOUSE_DB,
                username=settings.CLICKHOUSE_USER,
                password=settings.CLICKHOUSE_PASSWORD
            )
            logger.info("ClickHouse connection successful")

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    @contextmanager
    def get_pg_connection(self):
        """Context manager for PostgreSQL connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"PostgreSQL error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_pg_cursor(self):
        """Context manager for PostgreSQL cursor"""
        with self.get_pg_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()

    def get_redis(self):
        """Get Redis client"""
        if not self.redis_client:
            self.initialize()
        return self.redis_client

    def get_clickhouse(self):
        """Get ClickHouse client"""
        if not self.clickhouse_client:
            self.initialize()
        return self.clickhouse_client


# Global database manager instance
db_manager = DatabaseManager()
