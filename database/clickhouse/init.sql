-- ClickHouse Database Schema for ApexWatch
-- This script initializes tables for storing LLM thought history and time-series analytics

-- ====================
-- LLM THOUGHTS HISTORY
-- ====================

CREATE TABLE IF NOT EXISTS llm_thoughts (
    id UUID DEFAULT generateUUIDv4(),
    token_id String,
    event_type String,
    event_id String,
    prompt String,
    thought String,
    model_used String,
    tokens_used UInt32,
    processing_time_ms UInt32,
    timestamp DateTime DEFAULT now(),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (token_id, timestamp)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 6 MONTH;

-- ====================
-- EVENT PROCESSING METRICS
-- ====================

CREATE TABLE IF NOT EXISTS event_metrics (
    id UUID DEFAULT generateUUIDv4(),
    event_type String,
    processing_time_ms UInt32,
    queue_wait_time_ms UInt32,
    success Boolean,
    error_message String,
    timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY timestamp
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 3 MONTH;

-- ====================
-- CONTEXT SNAPSHOTS
-- ====================

CREATE TABLE IF NOT EXISTS context_snapshots (
    id UUID DEFAULT generateUUIDv4(),
    token_id String,
    context_key String,
    context_data String,
    size_bytes UInt32,
    timestamp DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree()
ORDER BY (token_id, context_key, timestamp)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 1 MONTH;

-- ====================
-- SYSTEM METRICS
-- ====================

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID DEFAULT generateUUIDv4(),
    service_name String,
    metric_name String,
    metric_value Float64,
    tags Map(String, String),
    timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (service_name, metric_name, timestamp)
PARTITION BY toYYYYMM(timestamp)
TTL timestamp + INTERVAL 1 MONTH;

-- ====================
-- MATERIALIZED VIEWS FOR ANALYTICS
-- ====================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_thoughts_per_hour
ENGINE = SummingMergeTree()
ORDER BY (token_id, hour)
AS SELECT
    token_id,
    toStartOfHour(timestamp) as hour,
    count() as thought_count,
    avg(processing_time_ms) as avg_processing_time
FROM llm_thoughts
GROUP BY token_id, hour;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_event_success_rate
ENGINE = SummingMergeTree()
ORDER BY (event_type, hour)
AS SELECT
    event_type,
    toStartOfHour(timestamp) as hour,
    countIf(success = 1) as success_count,
    countIf(success = 0) as failure_count
FROM event_metrics
GROUP BY event_type, hour;

-- Create indexes for faster queries
ALTER TABLE llm_thoughts ADD INDEX idx_event_type event_type TYPE bloom_filter GRANULARITY 1;
ALTER TABLE event_metrics ADD INDEX idx_success success TYPE set(2) GRANULARITY 1;
