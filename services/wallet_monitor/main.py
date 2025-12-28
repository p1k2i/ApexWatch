"""
Wallet Monitor Service Main Application
FastAPI service with REST endpoints and background monitoring
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime
import threading
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor

from config import settings
from monitor import blockchain_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Starting Wallet Monitor Service...")

    try:
        # Initialize blockchain connection
        blockchain_monitor.initialize()

        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=blockchain_monitor.run_monitoring_loop,
            daemon=True
        )
        monitor_thread.start()

        logger.info("Wallet Monitor Service started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Wallet Monitor Service...")


# FastAPI app
app = FastAPI(
    title="ApexWatch Wallet Monitor",
    description="Monitors blockchain wallets and token transfers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection helper
def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )


# Security dependency
async def verify_access_key(x_access_key: str = Header(...)):
    """Verify the X-Access-Key header"""
    if x_access_key != settings.ACCESS_KEY:
        raise HTTPException(status_code=403, detail="Invalid access key")
    return x_access_key


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "timestamp": datetime.now().isoformat()
    }


# Get wallet summary for a token
@app.get("/api/wallets/summary/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_wallet_summary(token_id: str):
    """Get summary of watched wallets for a token"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get watched wallets
        cur.execute("""
            SELECT
                address, label, balance, is_whale,
                discovered_automatically, last_activity
            FROM watched_wallets
            WHERE token_id = %s
            ORDER BY balance DESC
            LIMIT 50
        """, (token_id,))

        wallets = []
        for row in cur.fetchall():
            wallets.append({
                "address": row['address'],
                "label": row['label'],
                "balance": float(row['balance']) if row['balance'] else 0,
                "is_whale": row['is_whale'],
                "discovered_automatically": row['discovered_automatically'],
                "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None
            })

        # Get recent transactions count
        cur.execute("""
            SELECT COUNT(*) as tx_count
            FROM wallet_transactions
            WHERE token_id = %s
        """, (token_id,))

        tx_count = cur.fetchone()['tx_count']

        cur.close()
        conn.close()

        return {
            "token_id": token_id,
            "watched_wallets_count": len(wallets),
            "total_transactions": tx_count,
            "wallets": wallets[:10]  # Return top 10
        }

    except Exception as e:
        logger.error(f"Error getting wallet summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get wallet details
@app.get("/api/wallets/{address}", dependencies=[Depends(verify_access_key)])
async def get_wallet_details(address: str, token_id: Optional[str] = None):
    """Get details for a specific wallet"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if token_id:
            cur.execute("""
                SELECT * FROM watched_wallets
                WHERE address = %s AND token_id = %s
            """, (address, token_id))
        else:
            cur.execute("""
                SELECT * FROM watched_wallets
                WHERE address = %s
            """, (address,))

        wallet = cur.fetchone()

        if not wallet:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Wallet not found")

        # Get recent transactions
        cur.execute("""
            SELECT
                from_address, to_address, amount, tx_hash,
                block_number, timestamp
            FROM wallet_transactions
            WHERE (from_address = %s OR to_address = %s)
                AND token_id = %s
            ORDER BY timestamp DESC
            LIMIT 20
        """, (address, address, str(wallet['token_id'])))

        transactions = []
        for row in cur.fetchall():
            transactions.append({
                "from": row['from_address'],
                "to": row['to_address'],
                "amount": float(row['amount']),
                "tx_hash": row['tx_hash'],
                "block_number": row['block_number'],
                "timestamp": row['timestamp'].isoformat()
            })

        cur.close()
        conn.close()

        return {
            "address": wallet['address'],
            "token_id": str(wallet['token_id']),
            "label": wallet['label'],
            "balance": float(wallet['balance']) if wallet['balance'] else 0,
            "is_whale": wallet['is_whale'],
            "discovered_automatically": wallet['discovered_automatically'],
            "last_activity": wallet['last_activity'].isoformat() if wallet['last_activity'] else None,
            "recent_transactions": transactions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get recent transactions
@app.get("/api/transactions/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_recent_transactions(token_id: str, limit: int = 50):
    """Get recent transactions for a token"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                from_address, to_address, amount, tx_hash,
                block_number, timestamp
            FROM wallet_transactions
            WHERE token_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (token_id, limit))

        transactions = []
        for row in cur.fetchall():
            transactions.append({
                "from": row['from_address'],
                "to": row['to_address'],
                "amount": float(row['amount']),
                "tx_hash": row['tx_hash'],
                "block_number": row['block_number'],
                "timestamp": row['timestamp'].isoformat()
            })

        cur.close()
        conn.close()

        return {
            "token_id": token_id,
            "transactions": transactions,
            "count": len(transactions)
        }

    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
