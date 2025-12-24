"""
News Monitor Service Main Application
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import sys
from datetime import datetime, timedelta
import threading
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings
from monitor import news_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="ApexWatch News Monitor",
    description="Monitors and filters news relevant to crypto tokens",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


async def verify_access_key(x_access_key: str = Header(...)):
    """Verify the X-Access-Key header"""
    if x_access_key != settings.ACCESS_KEY:
        raise HTTPException(status_code=403, detail="Invalid access key")
    return x_access_key


@app.on_event("startup")
async def startup_event():
    """Initialize and start monitoring"""
    logger.info("Starting News Monitor Service...")

    try:
        # Download NLTK data if needed (first run)
        try:
            import nltk
            nltk.download('punkt', quiet=True)
            nltk.download('brown', quiet=True)
        except:
            pass

        # Start monitoring in background
        monitor_thread = threading.Thread(
            target=news_monitor.run_monitoring_loop,
            daemon=True
        )
        monitor_thread.start()

        logger.info("News Monitor Service started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/news/recent/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_recent_news(token_id: str, limit: int = 20):
    """Get recent relevant news for a token"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                n.title, n.summary, n.url, n.relevance_score,
                n.sentiment_score, n.published_at,
                s.name as source_name
            FROM news_articles n
            JOIN news_sources s ON n.source_id = s.id
            WHERE n.token_id = %s AND n.is_relevant = TRUE
            ORDER BY n.published_at DESC
            LIMIT %s
        """, (token_id, limit))

        articles = []
        for row in cur.fetchall():
            articles.append({
                "title": row['title'],
                "summary": row['summary'],
                "url": row['url'],
                "source": row['source_name'],
                "relevance_score": float(row['relevance_score']) if row['relevance_score'] else 0,
                "sentiment_score": float(row['sentiment_score']) if row['sentiment_score'] else 0,
                "published_at": row['published_at'].isoformat() if row['published_at'] else None
            })

        cur.close()
        conn.close()

        return {
            "token_id": token_id,
            "articles": articles,
            "count": len(articles)
        }

    except Exception as e:
        logger.error(f"Error getting recent news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/search", dependencies=[Depends(verify_access_key)])
async def search_news(
    token_id: Optional[str] = None,
    keyword: Optional[str] = None,
    hours: int = 168  # Default 7 days
):
    """Search news articles"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        since = datetime.now() - timedelta(hours=hours)

        query = """
            SELECT
                n.title, n.summary, n.url, n.relevance_score,
                n.sentiment_score, n.published_at,
                s.name as source_name,
                t.symbol as token_symbol
            FROM news_articles n
            JOIN news_sources s ON n.source_id = s.id
            JOIN tokens t ON n.token_id = t.id
            WHERE n.published_at >= %s
        """
        params = [since]

        if token_id:
            query += " AND n.token_id = %s"
            params.append(token_id)

        if keyword:
            query += " AND (n.title ILIKE %s OR n.summary ILIKE %s)"
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern])

        query += " ORDER BY n.published_at DESC LIMIT 100"

        cur.execute(query, params)

        articles = []
        for row in cur.fetchall():
            articles.append({
                "title": row['title'],
                "summary": row['summary'],
                "url": row['url'],
                "source": row['source_name'],
                "token_symbol": row['token_symbol'],
                "relevance_score": float(row['relevance_score']) if row['relevance_score'] else 0,
                "sentiment_score": float(row['sentiment_score']) if row['sentiment_score'] else 0,
                "published_at": row['published_at'].isoformat() if row['published_at'] else None
            })

        cur.close()
        conn.close()

        return {
            "articles": articles,
            "count": len(articles),
            "filters": {
                "token_id": token_id,
                "keyword": keyword,
                "hours": hours
            }
        }

    except Exception as e:
        logger.error(f"Error searching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/news/refresh", dependencies=[Depends(verify_access_key)])
async def trigger_refresh():
    """Manually trigger a news refresh (for testing)"""
    try:
        # Trigger immediate processing in a separate thread
        refresh_thread = threading.Thread(
            target=lambda: news_monitor.process_all_sources_once(),
            daemon=True
        )
        refresh_thread.start()

        return {
            "status": "triggered",
            "message": "News refresh started",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error triggering refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources", dependencies=[Depends(verify_access_key)])
async def get_sources():
    """Get list of configured news sources"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT name, url, source_type, is_active
            FROM news_sources
            ORDER BY name
        """)

        sources = []
        for row in cur.fetchall():
            sources.append({
                "name": row['name'],
                "url": row['url'],
                "type": row['source_type'],
                "is_active": row['is_active']
            })

        cur.close()
        conn.close()

        return {
            "sources": sources,
            "count": len(sources)
        }

    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
