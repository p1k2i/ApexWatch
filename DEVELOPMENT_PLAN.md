# Comprehensive Development Plan for the Crypto Token Monitoring Bot Microservices "ApexWatch"

This document provides a detailed and professional development plan for each microservice in the Crypto Token Monitoring Bot project "ApexWatch". The plan focuses on the business logic, functional requirements, data flows, interactions, and integration points to enable precise recreation of the entire project. The architecture is microservice-based, with independent services communicating via REST APIs and webhooks. All services are containerized using Docker and orchestrated with docker-compose, ensuring isolation and scalability. Internal APIs are secured with an X-Access-Key header for authentication, except for the dashboard which uses JWT-based user authentication. Logging is centralized using the ELK stack (Elasticsearch for storage, Logstash for processing, and Kibana for visualization), with all services configured to send logs accordingly.

The system monitors a specific cryptocurrency token (initially ERC-20 on Ethereum), collects data from wallets, exchanges, and news sources, generates events, and processes them in a central service using an AI model (LLM) for contextual analysis. Events are handled sequentially to build and maintain context. Static data, analytics, and settings are stored in PostgreSQL; in-memory context in Redis; and LLM thought history in ClickHouse. Support for adding new crypto assets is modular, achieved through configuration updates in the dashboard and potential addition of new modules for non-EVM chains.

## Core Service

### Overview and Business Logic
The Core Service acts as the central "brain" of the bot, orchestrating event-driven processing for token monitoring and AI-based analysis. It receives events from peripheral microservices via webhooks, queues them for sequential handling to preserve context, invokes an LLM for thoughtful analysis, updates context and data stores, and exposes APIs for the dashboard and other services. The business goal is to build an incremental context over time, enabling the LLM to "think" step-by-step about token-related events (e.g., price changes, large transfers, news impacts) to generate insights, risks, or predictions stored for analytics.

### Functional Requirements
- **Event Reception and Queuing:** Expose a webhook endpoint to accept JSON events from peripheral services (e.g., {"type": "wallet_transfer", "data": {...}}). Validate the X-Access-Key header for security. Upon receipt, add the event to a persistent queue to ensure ordered processing without parallelism, maintaining contextual integrity.
- **Sequential Processing Loop:** Implement a worker that continuously checks the queue. For each event popped:
  - Load the current context from Redis (keyed by token identifier, e.g., partial contexts like recent thoughts or summaries).
  - If the context requires additional or fresh data (e.g., outdated news narrative based on timestamp checks), request it via REST APIs from the relevant peripheral service (e.g., GET to News Monitor for updated summaries).
  - Construct a prompt for the LLM by combining the loaded context with the new event (e.g., "Previous context: [redis_data]. New event: [event_details]. Analyze impacts on token value, risks, and next steps.").
  - Invoke the LLM using an OpenAI-compatible API (local or remote), passing the prompt to generate a "thought" (analytical response).
  - Store the generated thought in ClickHouse for historical querying (with timestamps, token ID, and event reference).
  - Update the in-memory context in Redis with the new thought (storing only relevant parts to avoid overflow, e.g., summarize older sections).
  - Persist any derived analytics or static data (e.g., updated token statistics) to PostgreSQL.
- **Context Management:** Contexts are segmented and loaded on-demand. If missing or stale (e.g., data older than a configurable threshold like one hour), trigger REST requests to refresh. This handles initial startups or recoveries from failures.
- **API Endpoints for Integration:**
  - GET endpoints to retrieve context sections from Redis or PostgreSQL (used by dashboard or LLM if needed).
  - GET for LLM thought history from ClickHouse (filtered by token, time range).
  - POST for updating settings from the dashboard (e.g., thresholds, new asset configs), which are stored in PostgreSQL and can trigger instant application or service restarts if necessary.
  - All endpoints require X-Access-Key validation.
- **Error Handling and Resilience:** Log all operations to ELK. Retry failed LLM calls or queue operations with exponential backoff. Ensure queue persistence to survive restarts.
- **Data Storage Integration:** Use PostgreSQL for static info (e.g., token configs, analytics aggregates), Redis for fast-access context, and ClickHouse for time-series LLM thoughts.

### Interactions
- Inbound: Webhooks from Wallet Monitor, Exchange Monitor, and News Monitor.
- Outbound: REST calls to peripheral services for data refreshes; LLM API invocations.
- With Dashboard: Expose APIs for real-time status (e.g., queue size via WebSockets), history, and settings management.

## Wallet Monitor Microservice

### Overview and Business Logic
The Wallet Monitor service focuses on discovering and tracking cryptocurrency wallets associated with the monitored token, particularly "whale" wallets (large holders). It polls or subscribes to blockchain data to detect significant transactions, filters them based on configurable parameters (e.g., transfer amounts in a range), and generates events for the Core Service. The business logic enables automatic wallet discovery (e.g., by transfer volume) and ongoing monitoring to identify patterns like accumulation or dumping, which feed into AI analysis for market insights.

### Functional Requirements
- **Configuration Loading:** Periodically or on startup, fetch token-specific settings from PostgreSQL via REST to the Core Service (e.g., token contract address, monitored wallet addresses, transfer thresholds like minimum/maximum amounts, time ranges).
- **Blockchain Monitoring:** Use blockchain APIs to subscribe to or poll for token transfers (initially ERC-20 on Ethereum). Focus on Transfer events, extracting from/to addresses, amounts (adjusted for decimals), and timestamps.
- **Automatic Wallet Discovery:** For each detected transfer, check if the amount falls within configured ranges. If yes, identify new wallets (not already in the monitored list) and automatically add them to PostgreSQL for persistent tracking. This enables dynamic expansion of monitoring scope.
- **Event Generation:** When a significant transfer occurs (e.g., exceeding threshold or matching discovery criteria), create a JSON event with details (type: "wallet_transfer", data: wallet addresses, amount, direction) and send it via webhook to the Core Service.
- **Data Caching and Storage:** Cache current balances and recent activities in PostgreSQL (shared table for watched wallets) to reduce API calls and enable quick queries.
- **API Endpoints:** Expose REST GET endpoints for current wallet data or manual refreshes (e.g., for dashboard queries), secured with X-Access-Key.
- **Error Handling:** Log API failures to ELK and implement retries. Handle rate limits by backoff strategies.

### Interactions
- Inbound: REST from Core Service or Dashboard for config updates.
- Outbound: Webhooks to Core Service for events; REST to blockchain providers.
- With Dashboard: Provide data for visualization of wallet activities.

## Exchange Monitor Microservice

### Overview and Business Logic
The Exchange Monitor service tracks market data for the token across multiple exchanges, including prices, trading volumes, and order book changes. It detects anomalies or significant shifts (e.g., price volatility) and generates events to inform the Core Service's AI analysis. The business logic supports unified access to diverse exchanges, allowing configurable monitoring to capture liquidity events or arbitrage opportunities.

### Functional Requirements
- **Configuration Loading:** Retrieve exchange-specific settings from PostgreSQL (e.g., list of exchanges, token symbols, monitoring thresholds like percentage price change).
- **Market Data Fetching:** Use a unified library to poll or subscribe to real-time data (tickers, order books, volumes) across supported exchanges. Normalize data (e.g., convert to USD equivalents if needed).
- **Anomaly Detection:** Compare current data against thresholds or historical baselines (stored in PostgreSQL). For example, if price changes exceed a configured percentage or volume spikes, flag it.
- **Event Generation:** Create JSON events for detected changes (type: "price_change" or "volume_spike", data: exchange name, new values, timestamp) and send via webhook to the Core Service.
- **Data Storage:** Persist historical snapshots in PostgreSQL for trend analysis and to compute baselines.
- **API Endpoints:** Provide REST GET for current market stats or historical data, secured with X-Access-Key.
- **Error Handling:** Log exchange API errors to ELK, with fallback to alternative exchanges if configured.

### Interactions
- Inbound: REST for config updates.
- Outbound: Webhooks to Core Service; API calls to exchanges.
- With Dashboard: Supply data for graphs and real-time updates.

## News Monitor Microservice

### Overview and Business Logic
The News Monitor service aggregates and filters news from economic and crypto sources, identifying items relevant to the token or broader market. It uses basic natural language processing to assess relevance and generates events for the Core Service to incorporate into contextual analysis (e.g., sentiment impact on token price). The business logic ensures timely, filtered insights to correlate external events with on-chain data.

### Functional Requirements
- **Configuration Loading:** Fetch settings from PostgreSQL (e.g., news sources, keywords for the token, polling frequency, relevance thresholds).
- **News Collection:** Periodically poll APIs or RSS feeds for new articles on crypto/economic topics.
- **Filtering and Analysis:** Apply keyword matching and simple NLP (e.g., token name mentions, sentiment scoring) to filter relevant news. Summarize if needed for event payloads.
- **Event Generation:** For relevant items, create JSON events (type: "news_update", data: title, summary, source, relevance score) and send via webhook to the Core Service.
- **Data Storage:** Cache recent news with timestamps in PostgreSQL, marking staleness for refresh requests.
- **API Endpoints:** Expose REST GET for fresh news or manual polling, and POST for on-demand refreshes, secured with X-Access-Key.
- **Error Handling:** Log source failures to ELK and skip unreliable feeds.

### Interactions
- Inbound: REST for configs or refresh requests from Core Service.
- Outbound: Webhooks to Core Service; API calls to news providers.
- With Dashboard: Provide news feeds for display.

## Dashboard Service

### Overview and Business Logic
The Dashboard Service provides a web-based console for users to view real-time monitoring data, historical analytics, LLM thoughts, and manage configurations. It supports visualization of token statistics, event queues, and AI processes, with secure access. The business logic centralizes control, allowing dynamic addition of new assets without code changes for compatible chains.

### Functional Requirements
- **User Authentication:** Implement login with username/password (stored hashed in PostgreSQL), issuing JWT tokens for sessions. No self-registration.
- **Data Visualization:** Fetch data via REST from Core Service and peripherals:
  - Display graphs (e.g., price trends from PostgreSQL).
  - Show event history, queue status (real-time via WebSockets), and LLM thought streams from ClickHouse.
  - Monitor incoming events, processing, and analytics.
- **Configuration Management:** Forms to edit settings (e.g., thresholds, add new asset configs like token address and chain). Save to PostgreSQL and notify services via REST for application (instant or with restart signals).
- **Asset Addition:** Interface for inputting new token details; for new chains, indicate need for manual module addition, but handle config storage automatically.
- **Real-Time Updates:** Use WebSockets for live feeds (e.g., queue changes, new thoughts).
- **API Interactions:** All outbound REST calls include X-Access-Key; handle JWT for user sessions.
- **Error Handling:** Log user actions and errors to ELK.

### Interactions
- Inbound: User interactions via web interface.
- Outbound: REST to Core Service and peripherals for data and updates.
- With Other Services: Acts as a client, not receiving direct inbound traffic.
