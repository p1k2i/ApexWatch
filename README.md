# ApexWatch - Crypto Token Monitoring Bot

![ApexWatch](https://img.shields.io/badge/ApexWatch-v1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

## 🎯 Overview

**ApexWatch** is a comprehensive, AI-powered cryptocurrency token monitoring system built with a microservices architecture. It monitors blockchain wallets, exchange markets, and news sources to provide real-time insights and AI-driven analysis using Large Language Models (LLMs).

### Key Features

- 🔍 **Automated Wallet Discovery** - Automatically identifies and tracks "whale" wallets based on transaction volumes
- 💹 **Multi-Exchange Monitoring** - Tracks prices, volumes, and anomalies across multiple exchanges
- 📰 **AI News Analysis** - Aggregates and filters crypto news with sentiment analysis
- 🤖 **LLM-Powered Insights** - Sequential event processing with contextual AI analysis
- 📊 **Real-Time Dashboard** - Beautiful Streamlit-based UI with live data visualization
- 🐳 **Fully Containerized** - Complete Docker orchestration with all dependencies
- 📈 **Scalable Architecture** - Microservices design for easy scaling and maintenance

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Dashboard (Streamlit)                 │
│                   JWT Auth • Real-time Charts                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Core Service                          │
│          Event Queue • LLM Processing • Context Mgmt         │
└─────────────────────────────────────────────────────────────┘
           │                  │                 │
    ┌──────┴──────┐    ┌─────┴─────┐    ┌─────┴──────┐
    ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Wallet │  │ Exchange │  │   News   │  │ RabbitMQ │
│Monitor │  │ Monitor  │  │ Monitor  │  │  Queue   │
└────────┘  └──────────┘  └──────────┘  └──────────┘
    │             │             │
    └─────────────┴─────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                            │
┌──────────┐  ┌───────┐  ┌──────────────┐
│PostgreSQL│  │ Redis │  │  ClickHouse  │
└──────────┘  └───────┘  └──────────────┘
```

### Components

1. **Core Service** - Central brain orchestrating event processing and LLM analysis
2. **Wallet Monitor** - Tracks blockchain transfers and discovers whale wallets
3. **Exchange Monitor** - Monitors market data across exchanges using CCXT
4. **News Monitor** - Aggregates news with NLP filtering and sentiment analysis
5. **Dashboard** - User interface for monitoring and configuration
6. **PostgreSQL** - Stores static data, configurations, and analytics
7. **Redis** - Caches real-time context for fast access
8. **ClickHouse** - Time-series storage for LLM thought history
9. **RabbitMQ** - Persistent message queue for sequential event processing
10. **ELK Stack** - Centralized logging (Elasticsearch, Logstash, Kibana)
11. **Ollama** - Local LLM service with fallback to OpenAI

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
- (Optional) Alchemy API key for Ethereum monitoring
- (Optional) OpenAI API key for LLM fallback

## 🚀 Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd ApexWatch

# Copy environment template
cp .env.template .env

# Edit .env with your API keys
nano .env  # or your preferred editor
```

### 2. Configure API Keys

Edit `.env` and set:

```bash
# Required for Ethereum monitoring
ALCHEMY_API_KEY=your_alchemy_api_key

# Optional for LLM fallback
OPENAI_API_KEY=your_openai_api_key

# Change these secrets in production!
ACCESS_KEY=your-secure-access-key
JWT_SECRET_KEY=your-secure-jwt-secret
```

### 3. Start the System

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Initialize Ollama (First Time Only)

```bash
# Pull the Llama 3 model
docker exec -it apexwatch-ollama ollama pull llama3

# Or use a smaller model
docker exec -it apexwatch-ollama ollama pull llama3:8b
```

### 5. Access the Dashboard

Open your browser and navigate to:

```
http://localhost:8501
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

**⚠️ IMPORTANT:** Change the default password immediately in production!

## 🔧 Service Endpoints

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Dashboard | 8501 | http://localhost:8501 | Web UI |
| Core Service | 8000 | http://localhost:8000 | Main API |
| Wallet Monitor | 8001 | http://localhost:8001 | Wallet API |
| Exchange Monitor | 8002 | http://localhost:8002 | Market API |
| News Monitor | 8003 | http://localhost:8003 | News API |
| PostgreSQL | 5432 | localhost:5432 | Database |
| Redis | 6379 | localhost:6379 | Cache |
| ClickHouse | 8123 | http://localhost:8123 | Analytics DB |
| RabbitMQ | 15672 | http://localhost:15672 | Queue Management |
| Kibana | 5601 | http://localhost:5601 | Log Viewer |

## 📊 Dashboard Features

### Overview Page
- Real-time queue status
- Current token prices across exchanges
- Watched wallet count
- Recent news count
- Price history charts
- Latest AI thoughts

### Wallets Page
- Top whale wallets
- Transaction history
- Balance tracking
- Auto-discovered wallets

### Market Page
- Multi-exchange price comparison
- Historical price charts
- Volume analysis
- Configurable time ranges

### News Page
- Filtered crypto news
- Relevance scoring
- Sentiment analysis
- Source tracking

### Settings Page
- Token configuration
- Monitoring thresholds
- System status
- Parameter tuning

## 🔒 Security

### Internal API Security

All internal service-to-service communication is protected by the `X-Access-Key` header. Set a strong access key in `.env`:

```bash
ACCESS_KEY=your-very-strong-secret-key-here
```

### Dashboard Security

The dashboard uses JWT-based authentication. Configure a strong secret:

```bash
JWT_SECRET_KEY=your-jwt-secret-key-here
```

### Database Security

Default PostgreSQL credentials are included for development. In production:

1. Change database passwords in `.env`
2. Use PostgreSQL's `pg_hba.conf` for access control
3. Enable SSL connections
4. Implement backup strategies

## 📝 Configuration

### Adding a New Token

1. Navigate to **Settings** → **Tokens** in the dashboard
2. Enter token details:
   - Symbol (e.g., USDT)
   - Name (e.g., Tether USD)
   - Contract Address
   - Chain (ethereum, polygon, bsc)
   - Decimals (usually 18 for ERC-20)

Or add directly to PostgreSQL:

```sql
INSERT INTO tokens (symbol, name, contract_address, chain, decimals, is_active)
VALUES ('USDT', 'Tether USD', '0xdac17f958d2ee523a2206206994597c13d831ec7', 'ethereum', 6, TRUE);
```

### Adjusting Monitoring Thresholds

Use the **Settings** → **Monitoring Settings** page to configure:

- **Minimum Transfer Amount** - Lower bound for wallet monitoring
- **Maximum Transfer Amount** - Upper bound for tracking
- **Price Change Threshold (%)** - Price movement to trigger alerts
- **Volume Spike Threshold (%)** - Volume increase to trigger events

### Configuring News Sources

Add news sources to PostgreSQL:

```sql
INSERT INTO news_sources (name, url, source_type, is_active)
VALUES ('CryptoNews', 'https://cryptonews.com/news/feed/', 'rss', TRUE);
```

### Adding Exchanges

Configure exchanges in PostgreSQL:

```sql
INSERT INTO exchange_configs (exchange_name, is_active, api_key, api_secret)
VALUES ('binance', TRUE, 'your_api_key', 'your_api_secret');
```

For public endpoints, API keys are optional.

## 🧪 Testing

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health  # Core
curl http://localhost:8001/health  # Wallet Monitor
curl http://localhost:8002/health  # Exchange Monitor
curl http://localhost:8003/health  # News Monitor
```

### Test Event Processing

```bash
# Send a test event to Core Service
curl -X POST http://localhost:8000/api/webhook/event \
  -H "X-Access-Key: your-access-key" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "price_change",
    "data": {
      "token_id": "your-token-id",
      "exchange": "binance",
      "old_price": 1.0,
      "new_price": 1.05,
      "change_percent": 5.0
    }
  }'
```

### View Queue Status

```bash
curl http://localhost:8000/api/queue/status \
  -H "X-Access-Key: your-access-key"
```

### Check LLM Thoughts

```bash
curl http://localhost:8000/api/thoughts/YOUR_TOKEN_ID \
  -H "X-Access-Key: your-access-key"
```

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs [service-name]

# Common issues:
# - Port conflicts: Change ports in docker-compose.yml
# - Memory: Increase Docker memory allocation
# - Database init: Ensure init.sql files are present
```

### Ollama Model Not Found

```bash
# Pull the model manually
docker exec -it apexwatch-ollama ollama pull llama3

# List available models
docker exec -it apexwatch-ollama ollama list
```

### Database Connection Errors

```bash
# Restart databases
docker-compose restart postgres redis clickhouse

# Check if databases are healthy
docker-compose ps

# Verify PostgreSQL initialization
docker exec -it apexwatch-postgres psql -U postgres -d apexwatch -c "\dt"
```

### No Events Being Processed

1. Check RabbitMQ queue: http://localhost:15672 (guest/guest)
2. Verify peripheral services are sending events
3. Check Core Service logs: `docker-compose logs core`
4. Ensure Alchemy API key is set for wallet monitoring

### Dashboard Not Loading

```bash
# Check dashboard logs
docker-compose logs dashboard

# Verify all API endpoints are accessible
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

## 📈 Monitoring and Logs

### Kibana (Log Viewer)

Access Kibana at http://localhost:5601

1. Create an index pattern: `apexwatch-logs-*`
2. Filter logs by service name
3. Set up dashboards for monitoring

### RabbitMQ Management

Access at http://localhost:15672 (guest/guest)

- View queue sizes
- Monitor message rates
- Check consumer connections

### ClickHouse Queries

```bash
# Connect to ClickHouse
docker exec -it apexwatch-clickhouse clickhouse-client

# Query thought history
SELECT event_type, count() as count
FROM llm_thoughts
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY event_type;

# View recent thoughts
SELECT timestamp, event_type, substring(thought, 1, 100) as thought_preview
FROM llm_thoughts
ORDER BY timestamp DESC
LIMIT 10;
```

## 🔄 Maintenance

### Backup Databases

```bash
# Backup PostgreSQL
docker exec apexwatch-postgres pg_dump -U postgres apexwatch > backup_$(date +%Y%m%d).sql

# Backup ClickHouse
docker exec apexwatch-clickhouse clickhouse-client --query "BACKUP DATABASE apexwatch TO Disk('backups', 'backup_$(date +%Y%m%d)')"
```

### Update Services

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Clear Old Data

```sql
-- PostgreSQL: Clear old market data
DELETE FROM market_data WHERE timestamp < NOW() - INTERVAL '30 days';

-- PostgreSQL: Clear old news
DELETE FROM news_articles WHERE published_at < NOW() - INTERVAL '60 days';
```

ClickHouse has automatic TTL configured in the schema.

## 🛠️ Development

### Project Structure

```
ApexWatch/
├── services/
│   ├── core/               # Core service
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── llm.py
│   │   ├── queue.py
│   │   ├── processor.py
│   │   └── Dockerfile
│   ├── wallet_monitor/     # Wallet monitoring
│   ├── exchange_monitor/   # Exchange monitoring
│   ├── news_monitor/       # News monitoring
│   └── dashboard/          # Dashboard UI
├── database/
│   ├── postgres/
│   │   └── init.sql
│   └── clickhouse/
│       └── init.sql
├── config/
│   └── logstash.conf
├── docker-compose.yml
├── .env.template
└── README.md
```

### Adding a New Monitor Service

1. Create a new directory under `services/`
2. Implement FastAPI service with monitoring logic
3. Add webhook calls to Core Service
4. Create Dockerfile
5. Add service to docker-compose.yml
6. Update network configuration

### Extending LLM Capabilities

Modify `services/core/llm.py`:
- Add new prompt templates
- Implement custom analysis functions
- Add additional LLM providers

### Custom Analytics

Add queries to `services/core/processor.py`:
- Calculate custom metrics
- Store in PostgreSQL or ClickHouse
- Expose via API endpoints

## 📚 API Documentation

### Core Service API

**POST /api/webhook/event**
```json
{
  "type": "wallet_transfer|price_change|volume_spike|news_update",
  "data": { /* event-specific data */ }
}
```

**GET /api/queue/status**
```json
{
  "queue_size": 10,
  "timestamp": "2024-12-24T10:00:00"
}
```

**GET /api/thoughts/{token_id}**
```json
{
  "thoughts": [
    {
      "thought": "Analysis text...",
      "event_type": "price_change",
      "timestamp": "2024-12-24T10:00:00"
    }
  ]
}
```

See service documentation for complete API reference.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is provided as-is for educational and commercial use.

## 🆘 Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review service logs
- Open an issue on GitHub

## 🎯 Roadmap

- [ ] Support for additional blockchains (Polygon, BSC, Solana)
- [ ] Advanced ML models for price prediction
- [ ] Mobile app for monitoring
- [ ] Telegram bot integration
- [ ] Advanced alert system
- [ ] Multi-user support with permissions
- [ ] API rate limiting
- [ ] Kubernetes deployment configs

## ⚠️ Disclaimer

This software is for informational purposes only. Cryptocurrency trading involves risk. Always do your own research and never invest more than you can afford to lose.

---

**Built with ❤️ using Python, FastAPI, Streamlit, and Docker**
