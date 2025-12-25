"""
Database functions for dashboard user preferences
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
from typing import Optional


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


def get_user_preference(username: str, preference_key: str) -> Optional[str]:
    """Get user preference from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT preference_value FROM user_preferences WHERE username = %s AND preference_key = %s",
            (username, preference_key)
        )

        result = cur.fetchone()
        cur.close()
        conn.close()

        return result['preference_value'] if result else None
    except Exception as e:
        print(f"Error getting user preference: {str(e)}")
        return None


def set_user_preference(username: str, preference_key: str, preference_value: str) -> bool:
    """Set user preference in database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Insert or update
        cur.execute("""
            INSERT INTO user_preferences (username, preference_key, preference_value)
            VALUES (%s, %s, %s)
            ON CONFLICT (username, preference_key)
            DO UPDATE SET preference_value = %s, updated_at = CURRENT_TIMESTAMP
        """, (username, preference_key, preference_value, preference_value))

        conn.commit()
        cur.close()
        conn.close()

        return True
    except Exception as e:
        print(f"Error setting user preference: {str(e)}")
        return False
