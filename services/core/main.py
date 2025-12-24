"""
Core Service Main Application
FastAPI application with webhook endpoints and background worker
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import sys
from datetime import datetime
import threading
import uvicorn

from config import settings
from database import db_manager
from queue_manager import queue_manager
from processor import event_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="ApexWatch Core Service",
    description="Central brain for crypto token monitoring with AI analysis",
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


# Pydantic models
class Event(BaseModel):
    type: str
    data: Dict[str, Any]


class SettingUpdate(BaseModel):
    token_id: str
    setting_key: str
    setting_value: str


# Security dependency
async def verify_access_key(x_access_key: str = Header(...)):
    """Verify the X-Access-Key header"""
    if x_access_key != settings.ACCESS_KEY:
        raise HTTPException(status_code=403, detail="Invalid access key")
    return x_access_key


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections and start background worker"""
    logger.info("Starting Core Service...")

    try:
        # Initialize database connections
        db_manager.initialize()

        # Connect to RabbitMQ
        queue_manager.connect()

        # Start event processing worker in background thread
        worker_thread = threading.Thread(
            target=start_event_worker,
            daemon=True
        )
        worker_thread.start()

        logger.info("Core Service started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


# Background worker
def start_event_worker():
    """Background worker to process events from queue"""
    logger.info("Starting event processing worker...")

    try:
        queue_manager.start_consuming(
            callback=event_processor.process_event
        )
    except Exception as e:
        logger.error(f"Event worker error: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Core Service...")
    queue_manager.close()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "timestamp": datetime.now().isoformat()
    }


# Webhook endpoint for receiving events
@app.post("/api/webhook/event", dependencies=[Depends(verify_access_key)])
async def receive_event(event: Event):
    """
    Receive events from peripheral services and add to queue
    """
    try:
        logger.info(f"Received event: {event.type}")

        # Add to queue
        queue_manager.publish_event(event.dict())

        return {
            "status": "queued",
            "event_type": event.type,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error receiving event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get queue status
@app.get("/api/queue/status", dependencies=[Depends(verify_access_key)])
async def get_queue_status():
    """Get current queue status"""
    try:
        queue_size = queue_manager.get_queue_size()

        return {
            "queue_size": queue_size,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get context for token
@app.get("/api/context/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_context(token_id: str):
    """Get current context for a token from Redis"""
    try:
        redis = db_manager.get_redis()
        context_key = f"context:{token_id}"

        context_json = redis.get(context_key)

        if not context_json:
            return {
                "token_id": token_id,
                "context": None,
                "message": "No context found"
            }

        import json
        context = json.loads(context_json)

        return {
            "token_id": token_id,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get thought history
@app.get("/api/thoughts/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_thought_history(
    token_id: str,
    limit: int = 50,
    offset: int = 0
):
    """Get LLM thought history for a token from ClickHouse"""
    try:
        ch = db_manager.get_clickhouse()

        query = f"""
            SELECT
                id, token_id, event_type, thought, model_used,
                tokens_used, processing_time_ms, timestamp
            FROM llm_thoughts
            WHERE token_id = '{token_id}'
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """

        result = ch.query(query)

        thoughts = []
        for row in result.result_rows:
            thoughts.append({
                "id": str(row[0]),
                "token_id": row[1],
                "event_type": row[2],
                "thought": row[3],
                "model_used": row[4],
                "tokens_used": row[5],
                "processing_time_ms": row[6],
                "timestamp": row[7].isoformat() if row[7] else None
            })

        return {
            "token_id": token_id,
            "thoughts": thoughts,
            "count": len(thoughts),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting thought history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get token analytics
@app.get("/api/analytics/{token_id}", dependencies=[Depends(verify_access_key)])
async def get_analytics(token_id: str, metric_name: Optional[str] = None):
    """Get analytics for a token from PostgreSQL"""
    try:
        with db_manager.get_pg_cursor() as cur:
            if metric_name:
                cur.execute("""
                    SELECT metric_name, metric_value, metadata, timestamp
                    FROM token_analytics
                    WHERE token_id = %s AND metric_name = %s
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (token_id, metric_name))
            else:
                cur.execute("""
                    SELECT metric_name, metric_value, metadata, timestamp
                    FROM token_analytics
                    WHERE token_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (token_id,))

            rows = cur.fetchall()

            analytics = []
            for row in rows:
                analytics.append({
                    "metric_name": row['metric_name'],
                    "metric_value": float(row['metric_value']) if row['metric_value'] else None,
                    "metadata": row['metadata'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None
                })

            return {
                "token_id": token_id,
                "analytics": analytics,
                "count": len(analytics)
            }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Update monitoring settings
@app.post("/api/settings/update", dependencies=[Depends(verify_access_key)])
async def update_setting(setting: SettingUpdate):
    """Update a monitoring setting in PostgreSQL"""
    try:
        with db_manager.get_pg_cursor() as cur:
            cur.execute("""
                INSERT INTO monitoring_settings (token_id, setting_key, setting_value, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (token_id, setting_key)
                DO UPDATE SET setting_value = %s, updated_at = %s
            """, (
                setting.token_id,
                setting.setting_key,
                setting.setting_value,
                datetime.now(),
                setting.setting_value,
                datetime.now()
            ))

        return {
            "status": "updated",
            "token_id": setting.token_id,
            "setting_key": setting.setting_key,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error updating setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Get all tokens
@app.get("/api/tokens", dependencies=[Depends(verify_access_key)])
async def get_tokens():
    """Get all configured tokens"""
    try:
        with db_manager.get_pg_cursor() as cur:
            cur.execute("""
                SELECT id, symbol, name, contract_address, chain, decimals, is_active
                FROM tokens
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)

            rows = cur.fetchall()

            tokens = []
            for row in rows:
                tokens.append({
                    "id": str(row['id']),
                    "symbol": row['symbol'],
                    "name": row['name'],
                    "contract_address": row['contract_address'],
                    "chain": row['chain'],
                    "decimals": row['decimals'],
                    "is_active": row['is_active']
                })

            return {
                "tokens": tokens,
                "count": len(tokens)
            }

    except Exception as e:
        logger.error(f"Error getting tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
