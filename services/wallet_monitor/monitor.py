"""
Blockchain Monitor using Web3.py
Monitors ERC-20 token transfers and manages wallet discovery
"""
import logging
from web3 import Web3
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import requests
import re
from config import settings
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# ERC-20 Transfer event signature
TRANSFER_EVENT_SIGNATURE = Web3.keccak(text="Transfer(address,address,uint256)").hex()

# ERC-20 ABI for balanceOf function
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]


def sanitize_logs(message: str) -> str:
    """Remove sensitive API keys from log messages"""
    if settings.ALCHEMY_API_KEY:
        message = message.replace(settings.ALCHEMY_API_KEY, "***SECRET***")
    return message

class BlockchainMonitor:
    """Monitors blockchain for token transfers"""

    def __init__(self):
        self.w3 = None
        self.db_params = {
            'host': settings.POSTGRES_HOST,
            'port': settings.POSTGRES_PORT,
            'database': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD
        }
        self.last_processed_block = {}

    def initialize(self):
        """Initialize Web3 connection"""
        try:
            # Build RPC URL with Alchemy key
            if settings.ALCHEMY_API_KEY:
                rpc_url = f"{settings.ETHEREUM_RPC_URL}{settings.ALCHEMY_API_KEY}"
            else:
                rpc_url = settings.ETHEREUM_RPC_URL
                logger.warning("No Alchemy API key configured, using default RPC")

            self.w3 = Web3(Web3.HTTPProvider(rpc_url))

            # Test connection by making an actual RPC call
            latest_block = self.w3.eth.block_number
            logger.info(f"Connected to Ethereum node, latest block: {latest_block}")

        except Exception as e:
            # Log detailed error information for connection failures
            error_type = type(e).__name__
            error_msg = str(e)

            # Extract HTTP status codes and meaningful error details
            if "429" in error_msg or "Too Many Requests" in error_msg:
                logger.error("Blockchain connection failed: HTTP 429 - Rate limit exceeded. Check your Alchemy API plan or wait before retrying.")
            elif "403" in error_msg or "Forbidden" in error_msg:
                logger.error("Blockchain connection failed: HTTP 403 - Access forbidden. Check your API key permissions.")
            elif "401" in error_msg or "Unauthorized" in error_msg:
                logger.error("Blockchain connection failed: HTTP 401 - Unauthorized. Verify your API key is correct.")
            elif "HTTPError" in error_type:
                logger.error(f"Blockchain connection failed: {error_type}: {sanitize_logs(error_msg)}")
            elif "ConnectionError" in error_type or "Timeout" in error_type:
                logger.error(f"Blockchain connection failed: {error_type} - Network connectivity issue: {sanitize_logs(error_msg)}")
            else:
                logger.error(f"Blockchain connection failed: {error_type}: {sanitize_logs(error_msg)}")

            raise

    def get_token_configs(self) -> List[Dict[str, Any]]:
        """Fetch active token configurations from database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, symbol, name, contract_address, chain, decimals
                FROM tokens
                WHERE is_active = TRUE AND chain = 'ethereum'
            """)

            tokens = cur.fetchall()
            cur.close()
            conn.close()

            return [dict(token) for token in tokens]

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

    def monitor_token_transfers(self, token_config: Dict[str, Any]):
        """Monitor transfers for a specific token"""
        token_id = str(token_config['id'])
        contract_address = token_config['contract_address']
        decimals = token_config['decimals']

        try:
            # Validate and checksum address
            try:
                checksum_address = Web3.to_checksum_address(contract_address)
            except Exception as e:
                logger.error(f"Invalid contract address for {token_config['symbol']}: {contract_address} - {e}")
                return

            # Get monitoring settings
            settings_dict = self.get_monitoring_settings(token_id)
            min_threshold = settings_dict.get('wallet_min_threshold', 1000000)
            max_threshold = settings_dict.get('wallet_max_threshold', 100000000000)

            # Get current block
            current_block = self.w3.eth.block_number

            # Determine start block
            if token_id not in self.last_processed_block:
                # Start from recent blocks on first run
                self.last_processed_block[token_id] = current_block - 100

            from_block = self.last_processed_block[token_id] + 1
            to_block = min(from_block + settings.MAX_BLOCKS_PER_SCAN - 1, current_block - settings.BLOCK_CONFIRMATION_COUNT)

            if from_block > to_block:
                return  # No new confirmed blocks

            logger.info(f"Scanning blocks {from_block} to {to_block} for {token_config['symbol']}")

            # Get transfer events
            filter_params = {
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': checksum_address,
                'topics': [TRANSFER_EVENT_SIGNATURE]
            }

            try:
                logs = self.w3.eth.get_logs(filter_params)
            except Exception as e:
                error_msg = f"Error getting logs for {token_config['symbol']}: {e}"
                if hasattr(e, 'response'):
                    error_msg += f" - {e.response.text}"
                logger.error(sanitize_logs(error_msg))
                return

            for log in logs:
                self.process_transfer_log(log, token_id, decimals, min_threshold, max_threshold)

            # Update last processed block
            self.last_processed_block[token_id] = to_block

            logger.info(f"Processed {len(logs)} transfers for {token_config['symbol']}")

        except Exception as e:
            logger.error(f"Error monitoring token {token_config['symbol']}: {e}")

    def process_transfer_log(self, log, token_id: str, decimals: int,
                            min_threshold: float, max_threshold: float):
        """Process a single transfer log entry"""
        try:
            # Decode transfer data
            topics = log['topics']
            from_address = '0x' + topics[1].hex()[-40:]
            to_address = '0x' + topics[2].hex()[-40:]
            amount_raw = int(log['data'].hex(), 16)
            amount = amount_raw / (10 ** decimals)

            tx_hash = log['transactionHash'].hex()
            block_number = log['blockNumber']

            # Get block timestamp
            block = self.w3.eth.get_block(block_number)
            timestamp = datetime.fromtimestamp(block['timestamp'])

            # Check if amount is within monitoring range
            if min_threshold <= amount_raw <= max_threshold:
                # Store transaction
                self.store_transaction(
                    token_id, from_address, to_address,
                    amount, tx_hash, block_number, timestamp
                )

                # Check for new wallets and auto-discovery
                self.discover_wallets(token_id, from_address, to_address, amount)

                # Generate event for Core Service
                self.send_event_to_core({
                    'type': 'wallet_transfer',
                    'data': {
                        'token_id': token_id,
                        'from_address': from_address,
                        'to_address': to_address,
                        'amount': amount,
                        'tx_hash': tx_hash,
                        'block_number': block_number,
                        'timestamp': timestamp.isoformat()
                    }
                })

                logger.info(f"Significant transfer: {amount} tokens from {from_address[:10]}... to {to_address[:10]}...")

        except Exception as e:
            logger.error(f"Error processing transfer log: {e}")

    def store_transaction(self, token_id: str, from_addr: str, to_addr: str,
                         amount: float, tx_hash: str, block_number: int, timestamp: datetime):
        """Store transaction in database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO wallet_transactions
                (token_id, from_address, to_address, amount, tx_hash, block_number, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO NOTHING
            """, (token_id, from_addr, to_addr, amount, tx_hash, block_number, timestamp))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing transaction: {e}")

    def discover_wallets(self, token_id: str, from_addr: str, to_addr: str, amount: float):
        """Automatic wallet discovery based on transaction amount"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Determine if this is a whale transaction (configurable threshold)
            is_whale = amount > 100000  # Example: 100k tokens

            # Check and add 'from' address if not exists
            cur.execute("""
                INSERT INTO watched_wallets (token_id, address, discovered_automatically, is_whale, last_activity)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (token_id, address)
                DO UPDATE SET last_activity = %s, is_whale = %s OR watched_wallets.is_whale
            """, (token_id, from_addr, True, is_whale, datetime.now(), datetime.now(), is_whale))

            # Check and add 'to' address if not exists
            cur.execute("""
                INSERT INTO watched_wallets (token_id, address, discovered_automatically, is_whale, last_activity)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (token_id, address)
                DO UPDATE SET last_activity = %s, is_whale = %s OR watched_wallets.is_whale
            """, (token_id, to_addr, True, is_whale, datetime.now(), datetime.now(), is_whale))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error in wallet discovery: {e}")

    def get_wallet_balance(self, wallet_address: str, contract_address: str, decimals: int) -> Optional[float]:
        """Fetch wallet balance for a specific token from blockchain"""
        try:
            if not self.w3 or not self.w3.is_connected():
                logger.error("Web3 connection not available")
                return None

            # Validate and checksum addresses
            wallet_checksum = Web3.to_checksum_address(wallet_address)
            contract_checksum = Web3.to_checksum_address(contract_address)

            # Create contract instance
            contract = self.w3.eth.contract(address=contract_checksum, abi=ERC20_ABI)

            # Call balanceOf function
            balance_raw = contract.functions.balanceOf(wallet_checksum).call()
            balance = balance_raw / (10 ** decimals)

            return balance

        except Exception as e:
            logger.error(f"Error fetching balance for {wallet_address[:10]}...: {e}")
            return None

    def update_wallet_balance(self, token_id: str, wallet_address: str, balance: float):
        """Update wallet balance in database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            cur.execute("""
                UPDATE watched_wallets
                SET balance = %s, updated_at = %s
                WHERE token_id = %s AND address = %s
            """, (balance, datetime.now(), token_id, wallet_address))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error updating wallet balance: {e}")

    def refresh_wallet_balances(self, token_config: Dict[str, Any]):
        """Refresh balances for all watched wallets of a token"""
        try:
            token_id = str(token_config['id'])
            contract_address = token_config['contract_address']
            decimals = token_config['decimals']

            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Get all watched wallets for this token
            cur.execute("""
                SELECT address FROM watched_wallets
                WHERE token_id = %s
                LIMIT 50
            """, (token_id,))

            wallets = cur.fetchall()
            cur.close()
            conn.close()

            if not wallets:
                return

            logger.info(f"Refreshing balances for {len(wallets)} wallets of token {token_config['symbol']}")

            # Update balance for each wallet
            for wallet in wallets:
                balance = self.get_wallet_balance(wallet['address'], contract_address, decimals)
                if balance is not None:
                    self.update_wallet_balance(token_id, wallet['address'], balance)
                    logger.debug(f"Updated balance for {wallet['address'][:10]}... to {balance}")

        except Exception as e:
            logger.error(f"Error refreshing wallet balances: {e}")

    def send_event_to_core(self, event: Dict[str, Any]):
        """Send event to Core Service via webhook"""
        try:
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/webhook/event",
                json=event,
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=10
            )
            response.raise_for_status()

        except Exception as e:
            logger.error(f"Failed to send event to Core Service: {e}")

    def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting wallet monitoring loop...")

        balance_refresh_counter = 0
        balance_refresh_interval = 10  # Refresh balances every 10 iterations

        while True:
            try:
                # Get active tokens
                tokens = self.get_token_configs()

                if not tokens:
                    logger.warning("No active tokens configured")
                else:
                    # Monitor each token
                    for token in tokens:
                        self.monitor_token_transfers(token)

                    # Periodically refresh wallet balances
                    balance_refresh_counter += 1
                    if balance_refresh_counter >= balance_refresh_interval:
                        logger.info("Refreshing wallet balances...")
                        for token in tokens:
                            self.refresh_wallet_balances(token)
                        balance_refresh_counter = 0

                # Wait before next iteration
                time.sleep(settings.POLL_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error


# Global monitor instance
blockchain_monitor = BlockchainMonitor()
