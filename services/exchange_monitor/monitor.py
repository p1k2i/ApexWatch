"""
Exchange Monitor using CCXT
Monitors token prices and volumes across multiple exchanges
"""
import logging
import ccxt
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import requests
from config import settings
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ExchangeMonitor:
    """Monitors exchanges for price and volume changes"""

    def __init__(self):
        self.exchanges = {}
        self.last_market_data = {}
        self.db_params = {
            'host': settings.POSTGRES_HOST,
            'port': settings.POSTGRES_PORT,
            'database': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD
        }

    def initialize(self):
        """Initialize exchange connections"""
        try:
            # Get configured exchanges from database
            exchange_configs = self.get_exchange_configs()

            for config in exchange_configs:
                exchange_name = config['exchange_name'].lower()

                try:
                    # Initialize CCXT exchange
                    if hasattr(ccxt, exchange_name):
                        exchange_class = getattr(ccxt, exchange_name)

                        # Initialize with API keys if provided
                        params = {}
                        if config.get('api_key') and config.get('api_secret'):
                            params['apiKey'] = config['api_key']
                            params['secret'] = config['api_secret']

                        self.exchanges[exchange_name] = exchange_class(params)
                        logger.info(f"Initialized exchange: {exchange_name}")
                    else:
                        logger.warning(f"Exchange {exchange_name} not supported by CCXT")

                except Exception as e:
                    logger.error(f"Failed to initialize {exchange_name}: {e}")

            if not self.exchanges:
                logger.warning("No exchanges initialized, using default exchanges")
                # Initialize some default exchanges without API keys
                self.exchanges['binance'] = ccxt.binance()
                self.exchanges['coinbase'] = ccxt.coinbase()

        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {e}")
            raise

    def get_exchange_configs(self) -> List[Dict[str, Any]]:
        """Get exchange configurations from database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT exchange_name, api_key, api_secret, is_active
                FROM exchange_configs
                WHERE is_active = TRUE
            """)

            configs = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()

            return configs

        except Exception as e:
            logger.error(f"Error fetching exchange configs: {e}")
            return []

    def get_token_configs(self) -> List[Dict[str, Any]]:
        """Get token configurations from database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, symbol, name
                FROM tokens
                WHERE is_active = TRUE
            """)

            tokens = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()

            return tokens

        except Exception as e:
            logger.error(f"Error fetching token configs: {e}")
            return []

    def get_monitoring_settings(self, token_id: str) -> Dict[str, Any]:
        """Get monitoring settings for a token"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT setting_key, setting_value
                FROM monitoring_settings
                WHERE token_id = %s
            """, (token_id,))

            rows = cur.fetchall()
            cur.close()
            conn.close()

            settings_dict = {}
            for row in rows:
                try:
                    settings_dict[row['setting_key']] = float(row['setting_value'])
                except ValueError:
                    settings_dict[row['setting_key']] = row['setting_value']

            return settings_dict

        except Exception as e:
            logger.error(f"Error fetching monitoring settings: {e}")
            return {}

    def fetch_market_data(self, exchange_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current market data for a symbol from an exchange"""
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return None

            # Fetch ticker data
            ticker = exchange.fetch_ticker(symbol)

            return {
                'price': ticker.get('last'),
                'volume_24h': ticker.get('quoteVolume'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high_24h': ticker.get('high'),
                'low_24h': ticker.get('low'),
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.warning(f"Failed to fetch data from {exchange_name} for {symbol}: {e}")
            return None

    def store_market_data(self, token_id: str, exchange_name: str, data: Dict[str, Any]):
        """Store market data in database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO market_data
                (token_id, exchange_name, price, volume_24h, bid, ask, high_24h, low_24h, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                token_id, exchange_name,
                data.get('price'), data.get('volume_24h'),
                data.get('bid'), data.get('ask'),
                data.get('high_24h'), data.get('low_24h'),
                data.get('timestamp')
            ))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing market data: {e}")

    def detect_anomalies(self, token_id: str, exchange_name: str,
                        current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect price changes and volume spikes"""
        anomalies = []
        key = f"{token_id}:{exchange_name}"

        # Get previous data
        previous_data = self.last_market_data.get(key)

        if not previous_data:
            # First data point, just store it
            self.last_market_data[key] = current_data
            return anomalies

        # Get thresholds
        settings_dict = self.get_monitoring_settings(token_id)
        price_threshold = settings_dict.get('price_change_threshold', settings.PRICE_CHANGE_THRESHOLD)
        volume_threshold = settings_dict.get('volume_spike_threshold', settings.VOLUME_SPIKE_THRESHOLD)

        # Check price change
        if previous_data.get('price') and current_data.get('price'):
            old_price = previous_data['price']
            new_price = current_data['price']

            if old_price > 0:
                change_percent = ((new_price - old_price) / old_price) * 100

                if abs(change_percent) >= price_threshold:
                    anomalies.append({
                        'type': 'price_change',
                        'data': {
                            'token_id': token_id,
                            'exchange': exchange_name,
                            'old_price': old_price,
                            'new_price': new_price,
                            'change_percent': round(change_percent, 2),
                            'volume': current_data.get('volume_24h'),
                            'timestamp': current_data['timestamp'].isoformat()
                        }
                    })

        # Check volume spike
        if previous_data.get('volume_24h') and current_data.get('volume_24h'):
            old_volume = previous_data['volume_24h']
            new_volume = current_data['volume_24h']

            if old_volume > 0:
                increase_percent = ((new_volume - old_volume) / old_volume) * 100

                if increase_percent >= volume_threshold:
                    anomalies.append({
                        'type': 'volume_spike',
                        'data': {
                            'token_id': token_id,
                            'exchange': exchange_name,
                            'old_volume': old_volume,
                            'new_volume': new_volume,
                            'increase_percent': round(increase_percent, 2),
                            'timestamp': current_data['timestamp'].isoformat()
                        }
                    })

        # Update last data
        self.last_market_data[key] = current_data

        return anomalies

    def send_event_to_core(self, event: Dict[str, Any]):
        """Send event to Core Service"""
        try:
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/webhook/event",
                json=event,
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Sent {event['type']} event to Core Service")

        except Exception as e:
            logger.error(f"Failed to send event to Core Service: {e}")

    def monitor_token(self, token_config: Dict[str, Any]):
        """Monitor a specific token across all exchanges"""
        token_id = str(token_config['id'])
        symbol = token_config['symbol']

        # Common trading pairs to try
        trading_pairs = [
            f"{symbol}/USDT",
            f"{symbol}/USD",
            f"{symbol}/BTC",
            f"{symbol}/ETH"
        ]

        for exchange_name, exchange in self.exchanges.items():
            try:
                # Load markets if not loaded
                if not exchange.markets:
                    exchange.load_markets()

                # Find available trading pair
                available_pair = None
                for pair in trading_pairs:
                    if pair in exchange.markets:
                        available_pair = pair
                        break

                if not available_pair:
                    continue

                # Fetch market data
                market_data = self.fetch_market_data(exchange_name, available_pair)

                if market_data:
                    # Store data
                    self.store_market_data(token_id, exchange_name, market_data)

                    # Detect anomalies
                    anomalies = self.detect_anomalies(token_id, exchange_name, market_data)

                    # Send events for detected anomalies
                    for anomaly in anomalies:
                        self.send_event_to_core(anomaly)
                        logger.info(f"Detected {anomaly['type']} for {symbol} on {exchange_name}")

            except Exception as e:
                logger.warning(f"Error monitoring {symbol} on {exchange_name}: {e}")

    def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting exchange monitoring loop...")

        while True:
            try:
                # Get active tokens
                tokens = self.get_token_configs()

                if not tokens:
                    logger.warning("No active tokens configured")
                else:
                    # Monitor each token
                    for token in tokens:
                        self.monitor_token(token)

                # Wait before next iteration
                time.sleep(settings.POLL_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)


# Global monitor instance
exchange_monitor = ExchangeMonitor()
