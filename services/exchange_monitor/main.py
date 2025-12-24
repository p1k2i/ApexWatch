"""
Exchange Monitor Service Main Application
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
from monitor import exchange_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="ApexWatch Exchange Monitor",
    description="Monitors token prices and volumes across exchanges",
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
    logger.info("Starting Exchange Monitor Service...")

    try:
        # Initialize exchanges
        exchange_monitor.initialize()

        # Start monitoring in background
        monitor_thread = threading.Thread(
            target=exchange_monitor.run_monitoring_loop,
            daemon=True
        )
        monitor_thread.start()

        logger.info("Exchange Monitor Service started successfully")

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


@app.get("/api/market/latest/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_latest_market_data(token_id: str):
    """Get latest market data for a token across all exchanges"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT DISTINCT ON (exchange_name)
                exchange_name, price, volume_24h, high_24h, low_24h, timestamp
            FROM market_data
            WHERE token_id = %s
            ORDER BY exchange_name, timestamp DESC
        """, (token_id,))

        markets = []
        for row in cur.fetchall():
            markets.append({
                "exchange": row['exchange_name'],
                "price": float(row['price']) if row['price'] else None,
                "volume_24h": float(row['volume_24h']) if row['volume_24h'] else None,
                "high_24h": float(row['high_24h']) if row['high_24h'] else None,
                "low_24h": float(row['low_24h']) if row['low_24h'] else None,
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None
            })

        cur.close()
        conn.close()

        return {
            "token_id": token_id,
            "markets": markets,
            "count": len(markets)
        }

    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/history/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_market_history(
    token_id: str,
    exchange: Optional[str] = None,
    hours: int = 24
):
    """Get historical market data for a token"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        since = datetime.now() - timedelta(hours=hours)

        if exchange:
            cur.execute("""
                SELECT exchange_name, price, volume_24h, timestamp
                FROM market_data
                WHERE token_id = %s
                    AND exchange_name = %s
                    AND timestamp >= %s
                ORDER BY timestamp ASC
            """, (token_id, exchange, since))
        else:
            cur.execute("""
                SELECT exchange_name, price, volume_24h, timestamp
                FROM market_data
                WHERE token_id = %s AND timestamp >= %s
                ORDER BY timestamp ASC
            """, (token_id, since))

        history = []
        for row in cur.fetchall():
            history.append({
                "exchange": row['exchange_name'],
                "price": float(row['price']) if row['price'] else None,
                "volume_24h": float(row['volume_24h']) if row['volume_24h'] else None,
                "timestamp": row['timestamp'].isoformat()
            })

        cur.close()
        conn.close()

        return {
            "token_id": token_id,
            "exchange": exchange,
            "hours": hours,
            "data": history,
            "count": len(history)
        }

    except Exception as e:
        logger.error(f"Error getting market history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exchanges", dependencies=[Depends(verify_access_key)])
async def get_exchanges():
    """Get list of configured exchanges"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT exchange_name, is_active
            FROM exchange_configs
            ORDER BY exchange_name
        """)

        exchanges = []
        for row in cur.fetchall():
            exchanges.append({
                "name": row['exchange_name'],
                "is_active": row['is_active']
            })

        cur.close()
        conn.close()

        return {
            "exchanges": exchanges,
            "count": len(exchanges)
        }

    except Exception as e:
        logger.error(f"Error getting exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
