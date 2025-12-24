"""
Event Processor
Handles sequential event processing with LLM analysis and context management
"""
import logging
import json
from typing import Dict, Any
from datetime import datetime, timedelta
import requests
from database import db_manager
from llm import llm_client
from config import settings
import uuid

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes events sequentially with context management"""

    def __init__(self):
        self.context_staleness_hours = settings.CONTEXT_STALENESS_HOURS

    def process_event(self, event: Dict[str, Any]):
        """
        Main event processing pipeline

        Args:
            event: Event dictionary with type and data
        """
        event_start = datetime.now()
        event_type = event.get('type', 'unknown')
        event_data = event.get('data', {})
        token_id = event_data.get('token_id')

        if not token_id:
            logger.warning(f"Event missing token_id: {event}")
            return

        try:
            # Step 1: Load current context from Redis
            context = self._load_context(token_id)

            # Step 2: Check if context needs refresh
            if self._is_context_stale(context, event_type):
                context = self._refresh_context(token_id, event_type)

            # Step 3: Construct prompt for LLM
            prompt = self._construct_prompt(event_type, event_data)

            # Step 4: Generate LLM thought
            llm_result = llm_client.generate_thought(
                prompt=prompt,
                context=context.get('summary', '')
            )

            # Step 5: Store thought in ClickHouse
            self._store_thought(
                token_id=token_id,
                event_type=event_type,
                thought=llm_result['thought'],
                model=llm_result['model_used'],
                tokens=llm_result['tokens_used'],
                processing_time=llm_result['processing_time_ms']
            )

            # Step 6: Update context in Redis
            self._update_context(token_id, llm_result['thought'], event_type)

            # Step 7: Update analytics in PostgreSQL
            self._update_analytics(token_id, event_type, event_data)

            # Log event metrics
            processing_time = int((datetime.now() - event_start).total_seconds() * 1000)
            self._log_event_metric(event_type, processing_time, True, None)

            logger.info(f"Successfully processed {event_type} event in {processing_time}ms")

        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")
            processing_time = int((datetime.now() - event_start).total_seconds() * 1000)
            self._log_event_metric(event_type, processing_time, False, str(e))

    def _load_context(self, token_id: str) -> Dict[str, Any]:
        """Load context from Redis"""
        redis = db_manager.get_redis()
        context_key = f"context:{token_id}"

        context_json = redis.get(context_key)
        if context_json:
            return json.loads(context_json)

        return {
            'summary': '',
            'last_updated': None,
            'event_count': 0
        }

    def _is_context_stale(self, context: Dict[str, Any], event_type: str) -> bool:
        """Check if context needs refreshing"""
        if not context.get('last_updated'):
            return True

        last_updated = datetime.fromisoformat(context['last_updated'])
        staleness_threshold = datetime.now() - timedelta(hours=self.context_staleness_hours)

        return last_updated < staleness_threshold

    def _refresh_context(self, token_id: str, event_type: str) -> Dict[str, Any]:
        """Refresh context by fetching latest data from peripheral services"""
        context = {'summary': '', 'last_updated': datetime.now().isoformat(), 'event_count': 0}

        try:
            # Fetch latest market data
            if event_type in ['price_change', 'volume_spike']:
                market_data = self._fetch_latest_market_data(token_id)
                if market_data:
                    context['summary'] += f"\nLatest Market: {market_data}"

            # Fetch latest news
            if event_type == 'news_update':
                news_data = self._fetch_latest_news(token_id)
                if news_data:
                    context['summary'] += f"\nRecent News: {news_data}"

            # Fetch wallet activity summary
            if event_type == 'wallet_transfer':
                wallet_data = self._fetch_wallet_summary(token_id)
                if wallet_data:
                    context['summary'] += f"\nWallet Activity: {wallet_data}"

        except Exception as e:
            logger.warning(f"Error refreshing context: {e}")

        return context

    def _fetch_latest_market_data(self, token_id: str) -> str:
        """Fetch latest market data from Exchange Monitor"""
        try:
            response = requests.get(
                f"{settings.EXCHANGE_MONITOR_URL}/api/market/latest/{token_id}",
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data)
        except Exception as e:
            logger.warning(f"Failed to fetch market data: {e}")
        return ""

    def _fetch_latest_news(self, token_id: str) -> str:
        """Fetch latest news from News Monitor"""
        try:
            response = requests.get(
                f"{settings.NEWS_MONITOR_URL}/api/news/recent/{token_id}",
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data)
        except Exception as e:
            logger.warning(f"Failed to fetch news: {e}")
        return ""

    def _fetch_wallet_summary(self, token_id: str) -> str:
        """Fetch wallet activity summary from Wallet Monitor"""
        try:
            response = requests.get(
                f"{settings.WALLET_MONITOR_URL}/api/wallets/summary/{token_id}",
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return json.dumps(data)
        except Exception as e:
            logger.warning(f"Failed to fetch wallet data: {e}")
        return ""

    def _construct_prompt(self, event_type: str, event_data: Dict[str, Any]) -> str:
        """Construct prompt based on event type and data"""
        prompts = {
            'wallet_transfer': f"""
Large wallet transfer detected:
- From: {event_data.get('from_address', 'unknown')}
- To: {event_data.get('to_address', 'unknown')}
- Amount: {event_data.get('amount', 0)} tokens
- Transaction: {event_data.get('tx_hash', 'N/A')}
- Timestamp: {event_data.get('timestamp', 'N/A')}
""",
            'price_change': f"""
Significant price change detected:
- Exchange: {event_data.get('exchange', 'unknown')}
- Previous Price: ${event_data.get('old_price', 0)}
- New Price: ${event_data.get('new_price', 0)}
- Change: {event_data.get('change_percent', 0)}%
- Volume: {event_data.get('volume', 'N/A')}
""",
            'volume_spike': f"""
Trading volume spike detected:
- Exchange: {event_data.get('exchange', 'unknown')}
- Previous Volume: {event_data.get('old_volume', 0)}
- New Volume: {event_data.get('new_volume', 0)}
- Increase: {event_data.get('increase_percent', 0)}%
""",
            'news_update': f"""
Relevant news article detected:
- Title: {event_data.get('title', 'N/A')}
- Source: {event_data.get('source', 'unknown')}
- Summary: {event_data.get('summary', 'N/A')}
- Relevance Score: {event_data.get('relevance_score', 0)}
- Sentiment: {event_data.get('sentiment_score', 0)}
"""
        }

        return prompts.get(event_type, f"Unknown event type: {event_type}\nData: {json.dumps(event_data)}")

    def _store_thought(self, token_id: str, event_type: str, thought: str,
                       model: str, tokens: int, processing_time: int):
        """Store LLM thought in ClickHouse"""
        ch = db_manager.get_clickhouse()

        try:
            ch.insert('llm_thoughts', [[
                str(uuid.uuid4()),
                token_id,
                event_type,
                str(uuid.uuid4()),  # event_id
                "",  # prompt (optional, can be large)
                thought,
                model,
                tokens,
                processing_time,
                datetime.now(),
                datetime.now()
            ]], column_names=[
                'id', 'token_id', 'event_type', 'event_id', 'prompt',
                'thought', 'model_used', 'tokens_used', 'processing_time_ms',
                'timestamp', 'created_at'
            ])

        except Exception as e:
            logger.error(f"Failed to store thought in ClickHouse: {e}")

    def _update_context(self, token_id: str, thought: str, event_type: str):
        """Update context in Redis"""
        redis = db_manager.get_redis()
        context_key = f"context:{token_id}"

        # Load current context
        context = self._load_context(token_id)

        # Update with new thought (keep summary concise)
        existing_summary = context.get('summary', '')
        new_summary = f"{existing_summary}\n[{event_type}]: {thought[:200]}..."  # Truncate for size

        # Keep only recent parts if too large
        if len(new_summary) > settings.CONTEXT_MAX_SIZE_KB * 1024:
            new_summary = new_summary[-(settings.CONTEXT_MAX_SIZE_KB * 1024):]

        context = {
            'summary': new_summary,
            'last_updated': datetime.now().isoformat(),
            'event_count': context.get('event_count', 0) + 1,
            'last_event_type': event_type
        }

        # Store in Redis with expiration
        redis.setex(
            context_key,
            timedelta(hours=24),  # Keep context for 24 hours
            json.dumps(context)
        )

    def _update_analytics(self, token_id: str, event_type: str, event_data: Dict[str, Any]):
        """Update analytics in PostgreSQL"""
        try:
            with db_manager.get_pg_cursor() as cur:
                # Insert into events_log
                cur.execute("""
                    INSERT INTO events_log (token_id, event_type, event_data, processed, processed_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (token_id, event_type, json.dumps(event_data), True, datetime.now()))

                # Update token analytics based on event type
                if event_type == 'price_change':
                    cur.execute("""
                        INSERT INTO token_analytics (token_id, metric_name, metric_value, timestamp)
                        VALUES (%s, %s, %s, %s)
                    """, (token_id, 'price', event_data.get('new_price', 0), datetime.now()))

        except Exception as e:
            logger.error(f"Failed to update analytics: {e}")

    def _log_event_metric(self, event_type: str, processing_time: int,
                          success: bool, error_message: str):
        """Log event processing metrics to ClickHouse"""
        ch = db_manager.get_clickhouse()

        try:
            ch.insert('event_metrics', [[
                str(uuid.uuid4()),
                event_type,
                processing_time,
                0,  # queue_wait_time_ms
                success,
                error_message or "",
                datetime.now()
            ]], column_names=[
                'id', 'event_type', 'processing_time_ms', 'queue_wait_time_ms',
                'success', 'error_message', 'timestamp'
            ])

        except Exception as e:
            logger.error(f"Failed to log event metric: {e}")


# Global event processor instance
event_processor = EventProcessor()
