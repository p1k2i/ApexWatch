# ApexWatch Testing Guide

## 🧪 Testing Overview

This guide provides comprehensive testing instructions for the ApexWatch system.

## Quick Smoke Test

After deployment, run these quick tests:

```bash
# 1. Check all services are running
docker-compose ps

# 2. Test health endpoints
curl http://localhost:8000/health  # Core
curl http://localhost:8001/health  # Wallet Monitor
curl http://localhost:8002/health  # Exchange Monitor
curl http://localhost:8003/health  # News Monitor

# 3. Access dashboard
# Open http://localhost:8501 in browser
# Login with: admin / admin123

# 4. Check queue connection
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/queue/status
```

All tests passing? Your system is operational! ✅

## Detailed Testing

### 1. Database Connectivity Tests

**PostgreSQL:**
```bash
# Connect to database
docker exec -it apexwatch-postgres psql -U postgres -d apexwatch

# List tables
\dt

# Check token configuration
SELECT * FROM tokens;

# Check users
SELECT username, is_active FROM users;

# Exit
\q
```

**Redis:**
```bash
# Connect to Redis
docker exec -it apexwatch-redis redis-cli

# Test connection
PING  # Should return PONG

# Check keys
KEYS *

# Exit
exit
```

**ClickHouse:**
```bash
# Connect to ClickHouse
docker exec -it apexwatch-clickhouse clickhouse-client

# Show databases
SHOW DATABASES;

# Show tables
USE apexwatch;
SHOW TABLES;

# Query thoughts (if any)
SELECT count() FROM llm_thoughts;

# Exit
exit
```

### 2. Message Queue Test

**RabbitMQ:**

1. Open RabbitMQ Management: http://localhost:15672
2. Login: guest / guest
3. Check:
   - Queue `events_queue` exists
   - No dead-letter messages
   - Consumers connected

**Manual Queue Test:**
```bash
# Send a test event
curl -X POST http://localhost:8000/api/webhook/event \
  -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "price_change",
    "data": {
      "token_id": "test-token-id",
      "exchange": "binance",
      "old_price": 1.0,
      "new_price": 1.05,
      "change_percent": 5.0,
      "volume": 1000000,
      "timestamp": "'$(date -Iseconds)'"
    }
  }'

# Check queue status (should increment)
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/queue/status
```

### 3. LLM Integration Test

**Test Ollama:**
```bash
# List models
docker exec -it apexwatch-ollama ollama list

# Test generation
docker exec -it apexwatch-ollama ollama run llama3 "Hello, test message"

# Check Ollama API
curl http://localhost:11434/api/tags
```

**Test via Core Service:**

1. Send an event (see Queue Test above)
2. Wait 30 seconds for processing
3. Check thoughts:
```bash
# Get token ID first
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/tokens

# Get thoughts for token
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/thoughts/YOUR_TOKEN_ID
```

### 4. Wallet Monitor Test

**Setup:**
```bash
# Ensure you have an Alchemy API key in .env
# ALCHEMY_API_KEY=your_key_here
```

**Test wallet monitoring:**
```bash
# Get token ID
TOKEN_ID=$(docker exec apexwatch-postgres psql -U postgres -d apexwatch -t -c "SELECT id FROM tokens LIMIT 1;" | tr -d ' ')

# Check wallet summary
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8001/api/wallets/summary/$TOKEN_ID

# Check transactions
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8001/api/transactions/$TOKEN_ID
```

**Check logs:**
```bash
docker-compose logs wallet-monitor | tail -50
```

### 5. Exchange Monitor Test

**Test market data fetching:**
```bash
# Get token ID
TOKEN_ID=$(docker exec apexwatch-postgres psql -U postgres -d apexwatch -t -c "SELECT id FROM tokens LIMIT 1;" | tr -d ' ')

# Wait 2 minutes for initial data collection, then:
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8002/api/market/latest/$TOKEN_ID

# Check market history
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  "http://localhost:8002/api/market/history/$TOKEN_ID?hours=1"

# List exchanges
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8002/api/exchanges
```

**Check logs:**
```bash
docker-compose logs exchange-monitor | tail -50
```

### 6. News Monitor Test

**Test news fetching:**
```bash
# Get token ID
TOKEN_ID=$(docker exec apexwatch-postgres psql -U postgres -d apexwatch -t -c "SELECT id FROM tokens LIMIT 1;" | tr -d ' ')

# Wait 5 minutes for initial news collection, then:
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8003/api/news/recent/$TOKEN_ID

# Search news
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  "http://localhost:8003/api/news/search?keyword=crypto"

# List sources
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8003/api/sources

# Trigger manual refresh
curl -X POST -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8003/api/news/refresh
```

**Check logs:**
```bash
docker-compose logs news-monitor | tail -50
```

### 7. Dashboard Test

**Manual Testing:**

1. Open http://localhost:8501
2. Login with admin/admin123
3. Test each page:
   - **Overview**: Check all metrics load
   - **Wallets**: Verify wallet list and transactions
   - **Market**: Check price charts
   - **News**: View news articles
   - **Settings**: Try updating a threshold

**Screenshot Test:**
Take screenshots of each page to verify UI rendering.

### 8. Integration Test

**Complete Flow Test:**

```bash
#!/bin/bash
# save as test_integration.sh

set -e

echo "=== ApexWatch Integration Test ==="

# 1. Health checks
echo "1. Testing health endpoints..."
for port in 8000 8001 8002 8003; do
    curl -f http://localhost:$port/health > /dev/null
    echo "✓ Port $port healthy"
done

# 2. Get token
echo "2. Getting token ID..."
TOKEN_ID=$(docker exec apexwatch-postgres psql -U postgres -d apexwatch -t -c "SELECT id FROM tokens WHERE symbol='USDT' LIMIT 1;" | tr -d ' ')
echo "✓ Token ID: $TOKEN_ID"

# 3. Send test event
echo "3. Sending test event..."
curl -X POST http://localhost:8000/api/webhook/event \
  -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"price_change\",
    \"data\": {
      \"token_id\": \"$TOKEN_ID\",
      \"exchange\": \"test\",
      \"old_price\": 1.0,
      \"new_price\": 1.05,
      \"change_percent\": 5.0,
      \"volume\": 1000000,
      \"timestamp\": \"$(date -Iseconds)\"
    }
  }" > /dev/null
echo "✓ Event sent"

# 4. Wait for processing
echo "4. Waiting for event processing (30 seconds)..."
sleep 30

# 5. Check queue
echo "5. Checking queue..."
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/queue/status
echo ""

# 6. Check thoughts
echo "6. Checking AI thoughts..."
THOUGHTS=$(curl -s -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/thoughts/$TOKEN_ID | jq -r '.count')
echo "✓ Found $THOUGHTS thoughts"

echo ""
echo "=== Integration Test Complete ==="
```

Run the test:
```bash
chmod +x test_integration.sh
./test_integration.sh
```

### 9. Performance Test

**Load Testing with Apache Bench:**

```bash
# Install apache bench
sudo apt install apache2-utils

# Test Core API
ab -n 100 -c 10 http://localhost:8000/health

# Test with authentication (requires creating a test file)
echo '{"type":"price_change","data":{"token_id":"test","exchange":"test","old_price":1.0,"new_price":1.05,"change_percent":5.0}}' > test_event.json

ab -n 100 -c 10 -p test_event.json -T application/json \
  -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/webhook/event
```

**Monitor Resource Usage:**
```bash
# Watch Docker stats
docker stats

# Check specific service
docker stats apexwatch-core
```

### 10. Error Handling Test

**Test various error scenarios:**

```bash
# 1. Invalid access key
curl -X POST http://localhost:8000/api/webhook/event \
  -H "X-Access-Key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"type":"test","data":{}}'
# Expected: 403 Forbidden

# 2. Missing token_id
curl -X POST http://localhost:8000/api/webhook/event \
  -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"type":"price_change","data":{"exchange":"test"}}'
# Expected: 200 but event won't process (check logs)

# 3. Invalid token ID
curl -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/thoughts/invalid-id
# Expected: Empty results

# 4. Database connection test (restart postgres)
docker-compose restart postgres
sleep 10
curl http://localhost:8000/health
# Expected: Services reconnect automatically
```

## Test Data Setup

### Add Test Token

```bash
docker exec -it apexwatch-postgres psql -U postgres -d apexwatch << EOF
INSERT INTO tokens (symbol, name, contract_address, chain, decimals, is_active)
VALUES ('TEST', 'Test Token', '0x0000000000000000000000000000000000000001', 'ethereum', 18, TRUE)
ON CONFLICT DO NOTHING;
EOF
```

### Add Test Wallet

```bash
docker exec -it apexwatch-postgres psql -U postgres -d apexwatch << EOF
INSERT INTO watched_wallets (token_id, address, label, is_whale)
SELECT id, '0x0000000000000000000000000000000000000001', 'Test Whale', TRUE
FROM tokens WHERE symbol = 'TEST';
EOF
```

### Generate Sample Events

```bash
#!/bin/bash
# generate_test_events.sh

TOKEN_ID=$(docker exec apexwatch-postgres psql -U postgres -d apexwatch -t -c "SELECT id FROM tokens WHERE symbol='TEST' LIMIT 1;" | tr -d ' ')

for i in {1..10}; do
  PRICE=$(echo "scale=4; 1.0 + ($i * 0.01)" | bc)

  curl -X POST http://localhost:8000/api/webhook/event \
    -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
    -H "Content-Type: application/json" \
    -d "{
      \"type\": \"price_change\",
      \"data\": {
        \"token_id\": \"$TOKEN_ID\",
        \"exchange\": \"test_exchange\",
        \"old_price\": 1.0,
        \"new_price\": $PRICE,
        \"change_percent\": $(echo "$i * 1.0" | bc),
        \"timestamp\": \"$(date -Iseconds)\"
      }
    }"

  echo "Event $i sent"
  sleep 2
done
```

## Troubleshooting Tests

### Test Fails: Service Not Responding

```bash
# Check if service is running
docker-compose ps

# Check logs
docker-compose logs [service-name]

# Restart service
docker-compose restart [service-name]
```

### Test Fails: Database Connection

```bash
# Check database health
docker-compose ps postgres redis clickhouse

# Restart databases
docker-compose restart postgres redis clickhouse

# Wait for healthy status
sleep 30
```

### Test Fails: Queue Not Processing

```bash
# Check RabbitMQ
docker-compose logs rabbitmq

# Check Core Service worker
docker-compose logs core | grep "Processing event"

# Restart Core Service
docker-compose restart core
```

### Test Fails: LLM Not Responding

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check if model is pulled
docker exec -it apexwatch-ollama ollama list

# Pull model if missing
docker exec -it apexwatch-ollama ollama pull llama3

# Test Ollama directly
curl http://localhost:11434/api/tags
```

## Automated Testing Script

Save as `run_all_tests.sh`:

```bash
#!/bin/bash

set -e

echo "╔════════════════════════════════════╗"
echo "║  ApexWatch Automated Test Suite   ║"
echo "╚════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

test_passed() {
    echo -e "${GREEN}✓ $1${NC}"
}

test_failed() {
    echo -e "${RED}✗ $1${NC}"
}

# Test 1: Services Running
echo "Test 1: Checking services..."
if docker-compose ps | grep -q "Up"; then
    test_passed "Services are running"
else
    test_failed "Services not running"
    exit 1
fi

# Test 2: Health Endpoints
echo "Test 2: Testing health endpoints..."
for port in 8000 8001 8002 8003; do
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        test_passed "Port $port responding"
    else
        test_failed "Port $port not responding"
    fi
done

# Test 3: Database Connectivity
echo "Test 3: Testing databases..."
if docker exec apexwatch-postgres psql -U postgres -d apexwatch -c "SELECT 1" > /dev/null 2>&1; then
    test_passed "PostgreSQL accessible"
else
    test_failed "PostgreSQL not accessible"
fi

if docker exec apexwatch-redis redis-cli PING | grep -q "PONG"; then
    test_passed "Redis accessible"
else
    test_failed "Redis not accessible"
fi

# Test 4: Queue
echo "Test 4: Testing message queue..."
QUEUE_STATUS=$(curl -s -H "X-Access-Key: apexwatch-secret-key-change-in-production" \
  http://localhost:8000/api/queue/status)
if echo "$QUEUE_STATUS" | grep -q "queue_size"; then
    test_passed "Queue accessible"
else
    test_failed "Queue not accessible"
fi

# Test 5: Dashboard
echo "Test 5: Testing dashboard..."
if curl -f http://localhost:8501 > /dev/null 2>&1; then
    test_passed "Dashboard accessible"
else
    test_failed "Dashboard not accessible"
fi

echo ""
echo "Test suite complete!"
```

Make it executable and run:
```bash
chmod +x run_all_tests.sh
./run_all_tests.sh
```

## Continuous Monitoring

Set up ongoing testing with cron:

```bash
# Add to crontab
crontab -e

# Run tests every hour
0 * * * * /path/to/run_all_tests.sh >> /var/log/apexwatch-tests.log 2>&1
```

---

**For support with testing, check the logs and refer to the main README.md**
