"""
Authentication utilities for the dashboard
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings
from typing import Optional, Dict

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate a user"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, username, password_hash, is_active
            FROM users
            WHERE username = %s
        """, (username,))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not user['is_active']:
            return None

        # Verify password (using PostgreSQL's crypt function comparison)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT password_hash = crypt(%s, password_hash) as match
            FROM users
            WHERE username = %s
        """, (password, username))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0]:
            # Update last login
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE users SET last_login = %s WHERE username = %s
            """, (datetime.now(), username))
            conn.commit()
            cur.close()
            conn.close()

            return dict(user)

        return None

    except Exception as e:
        print(f"Authentication error: {e}")
        return None


def create_access_token(data: dict) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
