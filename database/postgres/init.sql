-- PostgreSQL Database Schema for ApexWatch
-- This script initializes all required tables for the crypto token monitoring system

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ====================
-- USERS & AUTHENTICATION
-- ====================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert default admin user (password: admin123 - CHANGE IN PRODUCTION)
INSERT INTO users (username, password_hash)
VALUES ('admin', crypt('admin123', gen_salt('bf')))
ON CONFLICT (username) DO NOTHING;

-- ====================
-- USER PREFERENCES
-- ====================

CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, preference_key)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_username ON user_preferences(username);
CREATE INDEX IF NOT EXISTS idx_user_preferences_key ON user_preferences(preference_key);

-- ====================
-- TOKEN CONFIGURATIONS
-- ====================

CREATE TABLE IF NOT EXISTS tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    contract_address VARCHAR(100) NOT NULL,
    chain VARCHAR(50) NOT NULL DEFAULT 'ethereum',
    decimals INTEGER DEFAULT 18,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contract_address, chain)
);

-- Insert sample token (USDT on Ethereum)
INSERT INTO tokens (symbol, name, contract_address, chain, decimals)
VALUES ('USDT', 'Tether USD', '0xdac17f958d2ee523a2206206994597c13d831ec7', 'ethereum', 6)
ON CONFLICT (contract_address, chain) DO NOTHING;

-- ====================
-- WALLET MONITORING
-- ====================

CREATE TABLE IF NOT EXISTS watched_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    address VARCHAR(100) NOT NULL,
    label VARCHAR(200),
    balance NUMERIC(38, 18) DEFAULT 0,
    last_activity TIMESTAMP,
    is_whale BOOLEAN DEFAULT FALSE,
    discovered_automatically BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(token_id, address)
);

CREATE INDEX idx_watched_wallets_token ON watched_wallets(token_id);
CREATE INDEX idx_watched_wallets_whale ON watched_wallets(is_whale);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    from_address VARCHAR(100) NOT NULL,
    to_address VARCHAR(100) NOT NULL,
    amount NUMERIC(38, 18) NOT NULL,
    tx_hash VARCHAR(100) UNIQUE NOT NULL,
    block_number BIGINT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wallet_tx_token ON wallet_transactions(token_id);
CREATE INDEX idx_wallet_tx_timestamp ON wallet_transactions(timestamp DESC);
CREATE INDEX idx_wallet_tx_from ON wallet_transactions(from_address);
CREATE INDEX idx_wallet_tx_to ON wallet_transactions(to_address);

-- ====================
-- EXCHANGE MONITORING
-- ====================

CREATE TABLE IF NOT EXISTS exchange_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange_name VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    api_key VARCHAR(255),
    api_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange_name)
);

-- Insert default exchanges
INSERT INTO exchange_configs (exchange_name, is_active)
VALUES
    ('binance', TRUE),
    ('coinbase', TRUE),
    ('kraken', TRUE)
ON CONFLICT (exchange_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    exchange_name VARCHAR(50) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    volume_24h NUMERIC(20, 8),
    bid NUMERIC(20, 8),
    ask NUMERIC(20, 8),
    high_24h NUMERIC(20, 8),
    low_24h NUMERIC(20, 8),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_market_data_token ON market_data(token_id);
CREATE INDEX idx_market_data_exchange ON market_data(exchange_name);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp DESC);

-- ====================
-- NEWS MONITORING
-- ====================

CREATE TABLE IF NOT EXISTS news_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    source_type VARCHAR(50) DEFAULT 'rss',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name)
);

-- Insert default news sources
INSERT INTO news_sources (name, url, source_type)
VALUES
    ('CoinDesk', 'https://www.coindesk.com/arc/outboundfeeds/rss/', 'rss'),
    ('CoinTelegraph', 'https://cointelegraph.com/rss', 'rss'),
    ('CryptoNews', 'https://cryptonews.com/news/feed/', 'rss')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    source_id UUID REFERENCES news_sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    url VARCHAR(1000),
    content TEXT,
    relevance_score NUMERIC(3, 2),
    sentiment_score NUMERIC(3, 2),
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW(),
    is_relevant BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_news_token ON news_articles(token_id);
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_relevant ON news_articles(is_relevant);

-- ====================
-- MONITORING CONFIGURATIONS
-- ====================

CREATE TABLE IF NOT EXISTS monitoring_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(token_id, setting_key)
);

-- Insert default monitoring settings for USDT
INSERT INTO monitoring_settings (token_id, setting_key, setting_value, description)
SELECT id, 'wallet_min_threshold', '1000000', 'Minimum transfer amount to track (in token base units)'
FROM tokens WHERE symbol = 'USDT'
ON CONFLICT (token_id, setting_key) DO NOTHING;

INSERT INTO monitoring_settings (token_id, setting_key, setting_value, description)
SELECT id, 'wallet_max_threshold', '100000000000', 'Maximum transfer amount to track'
FROM tokens WHERE symbol = 'USDT'
ON CONFLICT (token_id, setting_key) DO NOTHING;

INSERT INTO monitoring_settings (token_id, setting_key, setting_value, description)
SELECT id, 'price_change_threshold', '5.0', 'Price change percentage to trigger event'
FROM tokens WHERE symbol = 'USDT'
ON CONFLICT (token_id, setting_key) DO NOTHING;

INSERT INTO monitoring_settings (token_id, setting_key, setting_value, description)
SELECT id, 'volume_spike_threshold', '200.0', 'Volume increase percentage to trigger event'
FROM tokens WHERE symbol = 'USDT'
ON CONFLICT (token_id, setting_key) DO NOTHING;

INSERT INTO monitoring_settings (token_id, setting_key, setting_value, description)
SELECT id, 'context_staleness_hours', '1', 'Hours after which context is considered stale'
FROM tokens WHERE symbol = 'USDT'
ON CONFLICT (token_id, setting_key) DO NOTHING;

-- ====================
-- ANALYTICS
-- ====================

CREATE TABLE IF NOT EXISTS token_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(20, 8),
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_token ON token_analytics(token_id);
CREATE INDEX idx_analytics_metric ON token_analytics(metric_name);
CREATE INDEX idx_analytics_timestamp ON token_analytics(timestamp DESC);

-- ====================
-- EVENTS LOG
-- ====================

CREATE TABLE IF NOT EXISTS events_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES tokens(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_token ON events_log(token_id);
CREATE INDEX idx_events_type ON events_log(event_type);
CREATE INDEX idx_events_processed ON events_log(processed);
CREATE INDEX idx_events_created ON events_log(created_at DESC);

-- ====================
-- SYSTEM CONFIGURATION
-- ====================

CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert system configuration
INSERT INTO system_config (key, value, description)
VALUES
    ('llm_provider', 'ollama', 'Primary LLM provider: ollama or openai'),
    ('llm_model', 'llama3', 'LLM model name'),
    ('llm_fallback_provider', 'openai', 'Fallback LLM provider'),
    ('llm_fallback_model', 'gpt-4o-mini', 'Fallback LLM model'),
    ('ollama_url', 'http://ollama:11434', 'Ollama API endpoint'),
    ('access_key', 'apexwatch-secret-key-change-in-production', 'Internal API access key')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- ====================
-- VIEWS FOR ANALYTICS
-- ====================

CREATE OR REPLACE VIEW v_whale_activity AS
SELECT
    w.address,
    w.label,
    w.balance,
    t.symbol,
    t.name,
    COUNT(wt.id) as transaction_count,
    SUM(CASE WHEN wt.from_address = w.address THEN wt.amount ELSE 0 END) as total_sent,
    SUM(CASE WHEN wt.to_address = w.address THEN wt.amount ELSE 0 END) as total_received,
    MAX(wt.timestamp) as last_activity
FROM watched_wallets w
JOIN tokens t ON w.token_id = t.id
LEFT JOIN wallet_transactions wt ON (w.address = wt.from_address OR w.address = wt.to_address)
WHERE w.is_whale = TRUE
GROUP BY w.address, w.label, w.balance, t.symbol, t.name;

CREATE OR REPLACE VIEW v_latest_market_data AS
SELECT DISTINCT ON (token_id, exchange_name)
    token_id,
    exchange_name,
    price,
    volume_24h,
    high_24h,
    low_24h,
    timestamp
FROM market_data
ORDER BY token_id, exchange_name, timestamp DESC;

-- ====================
-- FUNCTIONS
-- ====================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_tokens_updated_at BEFORE UPDATE ON tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_watched_wallets_updated_at BEFORE UPDATE ON watched_wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exchange_configs_updated_at BEFORE UPDATE ON exchange_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_monitoring_settings_updated_at BEFORE UPDATE ON monitoring_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
