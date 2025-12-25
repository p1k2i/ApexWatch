# ApexWatch Data Analysis - Visualization Opportunities

## Overview
Your ApexWatch system has **multiple data sources** being collected across PostgreSQL and ClickHouse databases. Here's what you have and what's already visualized vs. what's missing.

---

## 📊 DATA SOURCES & CURRENT VISUALIZATIONS

### 1. **WALLET MONITORING DATA** ✅ Partially Visualized
**Database:** PostgreSQL (`watched_wallets`, `wallet_transactions`)

**Available Data:**
- Wallet addresses & balances
- Whale wallet detection (is_whale flag)
- Transaction history (from_address, to_address, amounts)
- Transaction timestamps & block numbers
- Whale discovery method (automatic vs manual)
- Last activity timestamp

**Currently Visualized:**
- ✅ Top whale wallet lists (table view)
- ✅ Recent transactions (table view)

**Missing Visualizations:**
- ❌ **Wallet balance trends over time** (line chart showing balance changes)
- ❌ **Transaction flow visualization** (Sankey diagram showing token flows)
- ❌ **Whale activity heatmap** (when whales are most active)
- ❌ **Wallet clustering** (grouping related wallets)
- ❌ **Transaction velocity** (transactions per hour/day)
- ❌ **Top sender/receiver analysis**
- ❌ **Wallet health metrics** (dormant vs active wallets)

---

### 2. **EXCHANGE & MARKET DATA** ✅ Partially Visualized
**Database:** PostgreSQL (`market_data`)

**Available Data:**
- Price (across multiple exchanges)
- Volume 24h
- Bid/Ask spreads
- High/Low 24h
- Exchange names
- Timestamps

**Currently Visualized:**
- ✅ Price comparison across exchanges (bar chart)
- ✅ Extended price history (line chart by exchange)

**Missing Visualizations:**
- ❌ **Bid-Ask spread analysis** (scatter or line chart)
- ❌ **Volume trends** (area chart showing 24h volume changes)
- ❌ **Price volatility** (standard deviation or Bollinger bands)
- ❌ **Exchange dominance** (pie chart of trading volume by exchange)
- ❌ **Price divergence detection** (when prices differ significantly)
- ❌ **Market depth visualization** (depth chart with bid/ask levels)
- ❌ **Exchange correlation matrix** (heatmap showing price correlations)

---

### 3. **NEWS & SENTIMENT DATA** ✅ Partially Visualized
**Database:** PostgreSQL (`news_articles`, `news_sources`)

**Available Data:**
- Article title, summary, content
- Source (CoinDesk, CoinTelegraph, etc.)
- Relevance score (0-1)
- Sentiment score (0-1)
- Published timestamp
- Article URL
- Is_relevant flag

**Currently Visualized:**
- ✅ Recent news list with sentiment metrics (expander view)
- ✅ Relevance & sentiment scores (text/metric display)

**Missing Visualizations:**
- ❌ **Sentiment timeline** (line chart of average sentiment over time)
- ❌ **News source distribution** (pie chart of articles by source)
- ❌ **Sentiment vs price correlation** (scatter showing relationship)
- ❌ **News frequency heatmap** (when news is published)
- ❌ **Sentiment word clouds** (most common words in articles)
- ❌ **Relevance score distribution** (histogram)
- ❌ **News impact analysis** (price movement after news)

---

### 4. **LLM THOUGHTS & ANALYTICS** ✅ Partially Visualized
**Database:** ClickHouse (`llm_thoughts`, `event_metrics`, `context_snapshots`)

**Available Data:**
- Thought content (AI-generated analysis)
- Event type (market_update, news_article, whale_activity, price_alert)
- Event ID & token ID
- Processing time (ms)
- Model used
- Tokens used
- Timestamp

**Also in ClickHouse:**
- Event processing metrics (processing time, wait time, success rate)
- System metrics (service performance)
- Materialized views for hourly aggregations

**Currently Visualized:**
- ✅ Thoughts list with filtering (UI list view)
- ✅ Thought detail view (expanded view)
- ✅ Event type filtering

**Missing Visualizations:**
- ❌ **AI thought frequency** (line chart: thoughts per hour/day)
- ❌ **Processing performance** (processing time trends)
- ❌ **Event type distribution** (pie/donut chart)
- ❌ **Success rate over time** (line chart with success/failure)
- ❌ **Model efficiency** (tokens used vs processing time)
- ❌ **Service health dashboard** (all system metrics combined)
- ❌ **Thought content analysis** (summary statistics of thoughts)

---

### 5. **USER & CONFIGURATION DATA** ❌ Not Visualized
**Database:** PostgreSQL (`users`, `user_preferences`, `monitoring_settings`)

**Available Data:**
- User login history
- User preferences
- Monitoring settings per token
- Token configurations (symbol, chain, decimals)
- Exchange configurations

**Missing Visualizations:**
- ❌ **User activity tracking** (login frequency, active periods)
- ❌ **Watched token list** (which tokens are monitored)
- ❌ **Configuration management UI** (visual settings editor)
- ❌ **System status overview** (all configured tokens & exchanges)

---

## 🎯 RECOMMENDED NEW VISUALIZATIONS (Priority Order)

### High Priority (Quick Wins)
1. **Wallet Balance Trends** - Area chart showing wallet balance evolution
2. **Sentiment vs Price Correlation** - Scatter plot with trend line
3. **Event Frequency Timeline** - Bar/line chart of events per time period
4. **News Sentiment Heatmap** - By date and sentiment level
5. **Exchange Volume Distribution** - Pie chart of trading volume

### Medium Priority (Value-Add)
6. **Processing Performance Dashboard** - LLM processing metrics
7. **Whale Activity Heatmap** - When whales are most active (day/hour)
8. **Transaction Flow Sankey** - Visual flow of tokens between wallets
9. **Price Volatility Comparison** - Standard deviation by exchange
10. **Service Health Monitor** - System metrics from ClickHouse

### Advanced (Enhancement)
11. **Sentiment Word Cloud** - Top keywords from articles
12. **ML-Powered Alerts** - Anomaly detection visualization
13. **Portfolio Analysis** (if user wallets tracked)
14. **Price Prediction Chart** - Historical with trend forecast

---

## 📈 QUICK WINS - WHAT YOU CAN ADD IMMEDIATELY

### 1. Dashboard Overview Page Enhancement
```
Add to overview.py or create new section:
- Total wallets tracked (metric)
- Price correlation matrix heatmap (exchanges)
- Average sentiment score (metric + trend)
- Total events processed today (metric)
- System uptime % (metric)
```

### 2. New Tab: "Analytics" Page
```
Combine:
- Event frequency timeline (last 7 days)
- Sentiment trend (last 30 days)
- Processing performance metrics
- Top news sources pie chart
```

### 3. Enhanced Market Page
```
Add:
- Bid-ask spread analysis over time
- Volume comparison chart
- Price volatility (rolling std dev)
- Exchange dominance (volume share)
```

### 4. Enhanced Wallet Page
```
Add:
- Balance history chart (selected wallet)
- Whale activity timeline
- Transaction distribution (in vs out)
- Top transaction pairs (from/to addresses)
```

### 5. Enhanced News Page
```
Add:
- Sentiment timeline (area chart)
- Sentiment distribution (histogram)
- Source distribution (pie)
- Relevance vs sentiment scatter
```

---

## 🛠️ IMPLEMENTATION NOTES

### Data Already Available
- All raw data is collected in PostgreSQL & ClickHouse
- You have historical data with timestamps
- ClickHouse has materialized views ready for aggregations
- Event metrics and processing times are tracked

### What You Need
1. **Aggregation queries** - To compute trends, averages, distributions
2. **API endpoints** - To serve aggregated data to dashboard
3. **Chart components** - Using Plotly (already imported in market.py)

### Example Query Pattern (PostgreSQL)
```sql
-- Wallet balance trends
SELECT
    w.address,
    DATE(wt.timestamp) as date,
    COUNT(*) as tx_count,
    SUM(CASE WHEN wt.from_address = w.address THEN -1 ELSE 1 END) as net_flow
FROM watched_wallets w
LEFT JOIN wallet_transactions wt ON w.id = wt.wallet_id
GROUP BY w.address, DATE(wt.timestamp)
ORDER BY date DESC;
```

### Example Query Pattern (ClickHouse)
```sql
-- Event frequency by hour
SELECT
    toStartOfHour(timestamp) as hour,
    event_type,
    COUNT(*) as count,
    avg(processing_time_ms) as avg_time
FROM llm_thoughts
GROUP BY hour, event_type
ORDER BY hour DESC;
```

---

## 📊 DATA SUMMARY

| Category | Tables | Records | Viz Status | Priority |
|----------|--------|---------|-----------|----------|
| Wallets | 2 | ~1000s | 30% | HIGH |
| Markets | 1 | ~10000s | 40% | HIGH |
| News | 2 | ~1000s | 20% | MEDIUM |
| LLM Thoughts | 3 | ~100000s | 25% | MEDIUM |
| Users/Config | 4 | ~100s | 0% | LOW |

---

## ✨ NEXT STEPS

1. **Create new "Analytics" page module** for system-wide metrics
2. **Build aggregation service** in core service for common queries
3. **Add 3-5 quick visualization** to existing pages
4. **Create ClickHouse aggregation queries** for performance metrics
5. **Implement real-time updates** using Streamlit's `st.cache_data`
