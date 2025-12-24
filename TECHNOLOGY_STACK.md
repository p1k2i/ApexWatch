**Technology Stack Footnote**

The entire system is built using a modern, production-grade Python-centric stack:
- **Backend**: Python 3.12 with FastAPI (Core Service and all microservices) for high-performance asynchronous APIs.
- **AI/LLM Integration**: OpenAI-compatible API client (primary: local Ollama with models such as Llama 3 8B; automatic fallback to remote OpenAI GPT-4o-mini or equivalent).
- **Blockchain Interaction**: Web3.py + Alchemy SDK (real-time transfers and notifications for ERC-20 tokens).
- **Exchange Data**: CCXT Pro/library for unified real-time and historical market data across centralized and decentralized exchanges.
- **Message Queue**: RabbitMQ as the persistent, reliable queue ensuring strictly sequential event processing in the Core Service.
- **Databases**:
  - PostgreSQL 17 – primary relational store for configurations, watched wallets, analytics, and settings.
  - Redis – in-memory storage for fast-access token-specific context and partial thought caching.
  - ClickHouse 25.10 – columnar database optimized for time-series storage and analytics of LLM thought history.
- **News & NLP**: Requests + Feedparser for RSS/API ingestion; lightweight NLTK/ spaCy-based filtering with optional LLM summarization.
- **Dashboard**: Streamlit (chosen for rapid MVP development, built-in Plotly charts, real-time WebSocket support, and simple JWT authentication).
- **Containerization & Orchestration**: Docker + docker-compose for all services, databases, RabbitMQ, and the full ELK stack.
- **Logging & Observability**: Centralized ELK Stack (Elasticsearch + Logstash + Kibana) for structured logs from every microservice.
- **Security**: Internal services protected by static X-Access-Key header middleware; Dashboard secured via JWT; all secrets managed through environment variables and docker-compose overrides.

This stack was deliberately chosen to balance development speed, operational reliability, cost efficiency (heavy use of local LLM and open-source components), and future extensibility to additional blockchains and assets.
