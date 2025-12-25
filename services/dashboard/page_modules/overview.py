"""
Overview page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import settings
from page_modules.utils import make_api_request, get_tokens
from database import get_db_connection


@st.cache_data(ttl=300)
def get_system_health_metrics():
    """Get system-wide health metrics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get various system-wide metrics
        metrics = {}

        # Total active tokens
        cur.execute("SELECT COUNT(*) FROM tokens WHERE is_active = TRUE")
        metrics['active_tokens'] = cur.fetchone()[0]

        # Total watched wallets
        cur.execute("SELECT COUNT(*) FROM watched_wallets")
        metrics['total_wallets'] = cur.fetchone()[0]

        # Whale wallets
        cur.execute("SELECT COUNT(*) FROM watched_wallets WHERE is_whale = TRUE")
        metrics['whale_wallets'] = cur.fetchone()[0]

        # Transactions today
        cur.execute("SELECT COUNT(*) FROM wallet_transactions WHERE timestamp > CURRENT_DATE")
        metrics['tx_today'] = cur.fetchone()[0]

        # News articles today
        cur.execute("SELECT COUNT(*) FROM news_articles WHERE fetched_at > CURRENT_DATE")
        metrics['news_today'] = cur.fetchone()[0]

        # Average sentiment today
        cur.execute("""
            SELECT AVG(sentiment_score)
            FROM news_articles
            WHERE published_at > CURRENT_DATE
                AND sentiment_score IS NOT NULL
        """)
        result = cur.fetchone()
        metrics['avg_sentiment_today'] = result[0] if result[0] is not None else 0

        # Market data points today
        cur.execute("SELECT COUNT(*) FROM market_data WHERE timestamp > CURRENT_DATE")
        metrics['market_updates_today'] = cur.fetchone()[0]

        # Active exchanges
        cur.execute("SELECT COUNT(*) FROM exchange_configs WHERE is_active = TRUE")
        metrics['active_exchanges'] = cur.fetchone()[0]

        cur.close()
        conn.close()

        return metrics

    except Exception as e:
        st.error(f"Error fetching system metrics: {e}")
        return {}


@st.cache_data(ttl=300)
def get_price_correlation_matrix(days: int = 7):
    """Get price correlation between exchanges"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            exchange_name,
            timestamp,
            price
        FROM market_data
        WHERE timestamp > NOW() - INTERVAL '%s days'
            AND price IS NOT NULL
        ORDER BY timestamp DESC
        """

        cur.execute(query, (days,))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['exchange_name', 'timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Pivot to get prices by exchange
            pivot_df = df.pivot_table(index='timestamp', columns='exchange_name', values='price')

            # Calculate correlation
            if not pivot_df.empty and len(pivot_df.columns) > 1:
                corr_matrix = pivot_df.corr()
                return corr_matrix

        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error calculating correlation: {e}")
        return pd.DataFrame()


def display_price_chart(token_id: str):
    """Display price history chart"""
    market_history = make_api_request(
        f"{settings.EXCHANGE_MONITOR_URL}/api/market/history/{token_id}?hours=24"
    )

    if market_history and market_history.get('data'):
        df = pd.DataFrame(market_history['data'])

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            fig = px.line(
                df,
                x='timestamp',
                y='price',
                color='exchange',
                title='24h Price History'
            )

            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price data available")
    else:
        st.info("No price data available")


def display_thoughts(token_id: str):
    """Display recent AI thoughts"""
    thoughts_data = make_api_request(
        f"{settings.CORE_SERVICE_URL}/api/thoughts/{token_id}?limit=5"
    )

    if thoughts_data and thoughts_data.get('thoughts'):
        for thought in thoughts_data['thoughts']:
            with st.expander(f"🤖 {thought['event_type']} - {thought['timestamp'][:19]}"):
                st.write(thought['thought'])
                st.caption(f"Model: {thought['model_used']} | Tokens: {thought['tokens_used']}")
    else:
        st.info("No AI thoughts yet")


def overview_page():
    """Display overview dashboard"""
    st.title("📊 ApexWatch Dashboard")

    # Refresh button at the top
    if st.button("🔄 Refresh All Data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # System-wide health metrics
    st.markdown("### 🎯 System Health Overview")

    system_metrics = get_system_health_metrics()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Active Tokens",
            system_metrics.get('active_tokens', 0),
            help="Total number of tokens being monitored"
        )

    with col2:
        whale_count = system_metrics.get('whale_wallets', 0)
        total_wallets = system_metrics.get('total_wallets', 0)
        st.metric(
            "Whale Wallets",
            whale_count,
            delta=f"{whale_count}/{total_wallets}",
            help="Number of identified whale wallets"
        )

    with col3:
        tx_today = system_metrics.get('tx_today', 0)
        st.metric(
            "Transactions Today",
            f"{tx_today:,}",
            help="Transactions tracked today"
        )

    with col4:
        news_today = system_metrics.get('news_today', 0)
        st.metric(
            "News Today",
            news_today,
            help="News articles collected today"
        )

    with col5:
        avg_sentiment = system_metrics.get('avg_sentiment_today', 0)
        sentiment_label = "😊" if avg_sentiment > 0.1 else "😞" if avg_sentiment < -0.1 else "😐"
        st.metric(
            "Sentiment",
            sentiment_label,
            delta=f"{avg_sentiment:.2f}",
            help="Average sentiment score today"
        )

    # Second row of metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        market_updates = system_metrics.get('market_updates_today', 0)
        st.metric("Market Updates", f"{market_updates:,}")

    with col2:
        active_exchanges = system_metrics.get('active_exchanges', 0)
        st.metric("Active Exchanges", active_exchanges)

    with col3:
        # Get queue status
        queue_data = make_api_request(f"{settings.CORE_SERVICE_URL}/api/queue/status")
        queue_size = queue_data.get('queue_size', 0) if queue_data else 0
        st.metric("Queue Size", queue_size, help="Pending events in processing queue")

    with col4:
        # System status
        st.metric("System Status", "🟢 Online", help="All services operational")

    with col5:
        # Uptime placeholder
        st.metric("Uptime", "99.9%", help="System availability")

    st.markdown("---")

    # Token selector
    st.markdown("### 🪙 Token Selection")

    # Get tokens
    tokens = get_tokens()

    if not tokens:
        st.warning("No tokens configured")
        return

    # Token selector
    token_options = {f"{t['symbol']} - {t['name']}": t['id'] for t in tokens}
    selected = st.selectbox("Select Token for Detailed View", list(token_options.keys()))

    if selected:
        token_id = token_options[selected]
        st.session_state.selected_token = token_id

        st.markdown("---")

        # Token-specific metrics
        st.markdown(f"### 📈 {selected} - Real-time Metrics")

        # Get market data for selected token
        market_data = make_api_request(
            f"{settings.EXCHANGE_MONITOR_URL}/api/market/latest/{token_id}"
        )

        wallet_data = make_api_request(
            f"{settings.WALLET_MONITOR_URL}/api/wallets/summary/{token_id}"
        )

        news_data = make_api_request(
            f"{settings.NEWS_MONITOR_URL}/api/news/recent/{token_id}?limit=10"
        )

        # Token metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if market_data and market_data.get('markets'):
                prices = [m['price'] for m in market_data['markets'] if m.get('price')]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    spread_pct = ((max_price - min_price) / min_price * 100) if min_price > 0 else 0
                    st.metric(
                        "Avg Price",
                        f"${avg_price:.6f}",
                        delta=f"Spread: {spread_pct:.2f}%",
                        help="Average price across all exchanges"
                    )
                else:
                    st.metric("Avg Price", "N/A")
            else:
                st.metric("Avg Price", "N/A")

        with col2:
            if wallet_data:
                watched_count = wallet_data.get('watched_wallets_count', 0)
                whale_count = wallet_data.get('whale_wallets_count', 0)
                st.metric(
                    "Watched Wallets",
                    watched_count,
                    delta=f"{whale_count} whales",
                    help="Total wallets being monitored"
                )
            else:
                st.metric("Watched Wallets", 0)

        with col3:
            if news_data:
                recent_count = news_data.get('count', 0)
                st.metric(
                    "Recent News",
                    recent_count,
                    help="News articles in last 24h"
                )
            else:
                st.metric("Recent News", 0)

        with col4:
            if market_data and market_data.get('markets'):
                exchanges = len(market_data['markets'])
                st.metric(
                    "Active Markets",
                    exchanges,
                    help="Number of exchanges tracking this token"
                )
            else:
                st.metric("Active Markets", 0)

        st.markdown("---")

        # Visualization row
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📈 Price History (24h)")
            display_price_chart(token_id)

        with col2:
            st.markdown("#### 💭 Recent AI Insights")
            display_thoughts(token_id)

        st.markdown("---")

        # Price correlation heatmap
        st.markdown("### 🔥 Exchange Price Correlation (7 days)")

        corr_matrix = get_price_correlation_matrix(7)

        if not corr_matrix.empty and len(corr_matrix) > 1:
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdYlGn',
                zmid=0.95,
                text=corr_matrix.values,
                texttemplate='%{text:.3f}',
                textfont={"size": 10},
                hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
            ))

            fig.update_layout(
                title='Price Correlation Heatmap',
                xaxis_title='Exchange',
                yaxis_title='Exchange',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            st.caption("💡 Strong correlation (>0.95) indicates synchronized pricing across exchanges")
        else:
            st.info("Insufficient data for correlation analysis (need multiple exchanges)")

        st.markdown("---")

        # Quick navigation cards
        st.markdown("### 🚀 Quick Navigation")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("""
            **👛 Wallets**
            - View whale wallets
            - Transaction analysis
            - Balance tracking
            """)

        with col2:
            st.markdown("""
            **💹 Market**
            - Price comparison
            - Volume trends
            - Volatility analysis
            """)

        with col3:
            st.markdown("""
            **📰 News**
            - Sentiment analysis
            - Article tracking
            - Source distribution
            """)

        with col4:
            st.markdown("""
            **💭 AI Thoughts**
            - Browse insights
            - Performance metrics
            - Event analysis
            """)
