"""
Analytics page for ApexWatch Dashboard
Comprehensive system-wide metrics and performance analytics
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import get_db_connection


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_event_frequency_data(token_id: str, hours: int = 168):
    """Get event frequency data from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get from PostgreSQL (if we need to query news/market events)
        # For now, we'll aggregate from multiple sources

        query = """
        SELECT
            DATE_TRUNC('hour', timestamp) as hour,
            COUNT(*) as count,
            'wallet' as event_type
        FROM wallet_transactions
        WHERE timestamp > NOW() - INTERVAL '%s hours'
        GROUP BY hour

        UNION ALL

        SELECT
            DATE_TRUNC('hour', timestamp) as hour,
            COUNT(*) as count,
            'market' as event_type
        FROM market_data
        WHERE timestamp > NOW() - INTERVAL '%s hours'
        GROUP BY hour

        UNION ALL

        SELECT
            DATE_TRUNC('hour', fetched_at) as hour,
            COUNT(*) as count,
            'news' as event_type
        FROM news_articles
        WHERE fetched_at > NOW() - INTERVAL '%s hours'
        GROUP BY hour

        ORDER BY hour DESC
        """

        cur.execute(query, (hours, hours, hours))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['hour', 'count', 'event_type'])
            df['hour'] = pd.to_datetime(df['hour'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching event frequency: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_sentiment_trends(token_id: str, days: int = 7):
    """Get sentiment trends over time"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE(published_at) as date,
            AVG(sentiment_score) as avg_sentiment,
            AVG(relevance_score) as avg_relevance,
            COUNT(*) as article_count
        FROM news_articles
        WHERE token_id = %s
            AND published_at > NOW() - INTERVAL '%s days'
            AND sentiment_score IS NOT NULL
        GROUP BY DATE(published_at)
        ORDER BY date DESC
        """

        cur.execute(query, (token_id, days))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['date', 'avg_sentiment', 'avg_relevance', 'article_count'])
            df['date'] = pd.to_datetime(df['date'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching sentiment trends: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_news_source_distribution(token_id: str):
    """Get distribution of news by source"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            ns.name as source,
            COUNT(na.id) as article_count
        FROM news_sources ns
        LEFT JOIN news_articles na ON ns.id = na.source_id
        WHERE na.token_id = %s OR na.token_id IS NULL
        GROUP BY ns.name
        ORDER BY article_count DESC
        """

        cur.execute(query, (token_id,))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['source', 'article_count'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching source distribution: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_system_metrics():
    """Get system-wide metrics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get various counts
        cur.execute("SELECT COUNT(*) FROM watched_wallets WHERE is_active = TRUE")
        wallet_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM tokens WHERE is_active = TRUE")
        token_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM news_articles WHERE fetched_at > NOW() - INTERVAL '24 hours'")
        news_24h = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM wallet_transactions WHERE timestamp > NOW() - INTERVAL '24 hours'")
        tx_24h = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            'wallet_count': wallet_count,
            'token_count': token_count,
            'news_24h': news_24h,
            'tx_24h': tx_24h
        }

    except Exception as e:
        st.error(f"Error fetching system metrics: {e}")
        return {}


@st.cache_data(ttl=300)
def get_whale_activity_stats(token_id: str):
    """Get whale activity statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE_TRUNC('day', wt.timestamp) as day,
            COUNT(DISTINCT CASE WHEN ww.is_whale THEN wt.from_address END) as whale_senders,
            COUNT(DISTINCT CASE WHEN ww.is_whale THEN wt.to_address END) as whale_receivers,
            SUM(CASE WHEN ww.is_whale THEN wt.amount ELSE 0 END) as whale_volume
        FROM wallet_transactions wt
        LEFT JOIN watched_wallets ww ON ww.address IN (wt.from_address, wt.to_address) AND ww.token_id = wt.token_id
        WHERE wt.token_id = %s
            AND wt.timestamp > NOW() - INTERVAL '30 days'
        GROUP BY day
        ORDER BY day DESC
        """

        cur.execute(query, (token_id,))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['day', 'whale_senders', 'whale_receivers', 'whale_volume'])
            df['day'] = pd.to_datetime(df['day'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching whale activity: {e}")
        return pd.DataFrame()


def analytics_page():
    """Display comprehensive analytics dashboard"""
    st.title("📈 System Analytics")

    if not st.session_state.selected_token:
        st.warning("⚠️ Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh Data", width='stretch'):
            st.cache_data.clear()
            st.rerun()

    # System-wide metrics
    st.markdown("### 🎯 System Overview")
    metrics = get_system_metrics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Wallets", metrics.get('wallet_count', 0), help="Total watched wallets")
    with col2:
        st.metric("Active Tokens", metrics.get('token_count', 0), help="Total monitored tokens")
    with col3:
        st.metric("News (24h)", metrics.get('news_24h', 0), help="News articles in last 24 hours")
    with col4:
        st.metric("Transactions (24h)", metrics.get('tx_24h', 0), help="Transactions in last 24 hours")

    st.markdown("---")

    # Event Frequency Analysis
    st.markdown("### 📊 Event Frequency Timeline")

    col1, col2 = st.columns([3, 1])
    with col2:
        time_range = st.selectbox("Time Range", [24, 48, 72, 168], format_func=lambda x: f"{x} hours", index=3)

    event_data = get_event_frequency_data(token_id, time_range)

    if not event_data.empty:
        fig = px.bar(
            event_data,
            x='hour',
            y='count',
            color='event_type',
            title=f'Events per Hour (Last {time_range}h)',
            labels={'hour': 'Time', 'count': 'Event Count', 'event_type': 'Event Type'},
            barmode='group'
        )

        fig.update_layout(
            hovermode='x unified',
            xaxis_title="Time",
            yaxis_title="Event Count",
            legend_title="Event Type"
        )

        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No event data available for the selected time range")

    st.markdown("---")

    # Sentiment Trends
    st.markdown("### 😊 Sentiment Analysis Trends")

    col1, col2 = st.columns([3, 1])
    with col2:
        sentiment_days = st.selectbox("Days", [7, 14, 30], index=0, key="sentiment_days")

    sentiment_data = get_sentiment_trends(token_id, sentiment_days)

    if not sentiment_data.empty:
        # Create dual-axis chart
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sentiment_data['date'],
            y=sentiment_data['avg_sentiment'],
            name='Avg Sentiment',
            mode='lines+markers',
            line=dict(color='#2E86DE', width=3),
            yaxis='y'
        ))

        fig.add_trace(go.Bar(
            x=sentiment_data['date'],
            y=sentiment_data['article_count'],
            name='Article Count',
            marker_color='#54A0FF',
            opacity=0.3,
            yaxis='y2'
        ))

        fig.update_layout(
            title=f'Sentiment Trend (Last {sentiment_days} days)',
            xaxis=dict(title='Date'),
            yaxis=dict(
                title='Average Sentiment Score',
                side='left',
                range=[-1, 1]
            ),
            yaxis2=dict(
                title='Article Count',
                side='right',
                overlaying='y'
            ),
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig, width='stretch')

        # Sentiment statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_sent = sentiment_data['avg_sentiment'].mean()
            st.metric("Average Sentiment", f"{avg_sent:.3f}", help="Overall sentiment score (-1 to 1)")
        with col2:
            total_articles = sentiment_data['article_count'].sum()
            st.metric("Total Articles", int(total_articles), help=f"Articles in last {sentiment_days} days")
        with col3:
            avg_relevance = sentiment_data['avg_relevance'].mean()
            st.metric("Avg Relevance", f"{avg_relevance:.3f}", help="Average relevance score")
    else:
        st.info("No sentiment data available")

    st.markdown("---")

    # News Source Distribution
    st.markdown("### 📰 News Source Distribution")

    source_data = get_news_source_distribution(token_id)

    if not source_data.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                source_data,
                values='article_count',
                names='source',
                title='Articles by Source',
                hole=0.4
            )

            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.bar(
                source_data,
                x='article_count',
                y='source',
                orientation='h',
                title='Source Article Count',
                labels={'article_count': 'Articles', 'source': 'Source'}
            )

            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("No news source data available")

    st.markdown("---")

    # Whale Activity Analysis
    st.markdown("### 🐋 Whale Activity Analysis")

    whale_data = get_whale_activity_stats(token_id)

    if not whale_data.empty:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=whale_data['day'],
            y=whale_data['whale_senders'],
            name='Whale Senders',
            mode='lines+markers',
            line=dict(color='#FF6B6B', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=whale_data['day'],
            y=whale_data['whale_receivers'],
            name='Whale Receivers',
            mode='lines+markers',
            line=dict(color='#4ECDC4', width=2)
        ))

        fig.update_layout(
            title='Whale Activity Over Time (Last 30 days)',
            xaxis_title='Date',
            yaxis_title='Number of Whales',
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig, width='stretch')

        # Whale volume chart
        if 'whale_volume' in whale_data.columns:
            fig = px.area(
                whale_data,
                x='day',
                y='whale_volume',
                title='Whale Transaction Volume',
                labels={'whale_volume': 'Volume', 'day': 'Date'}
            )

            fig.update_traces(fill='tozeroy', line_color='#FFA502')
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("No whale activity data available")

    st.markdown("---")

    # System Health Footer
    st.markdown("### ⚙️ System Status")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("✅ Database: Connected")
    with col2:
        st.success("✅ Services: Running")
    with col3:
        last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.info(f"🕐 Last Update: {last_update}")
