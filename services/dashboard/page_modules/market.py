"""
Market monitoring page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from config import settings
from page_modules.utils import make_api_request
from database import get_db_connection


@st.cache_data(ttl=300)
def get_volume_trends(token_id: str, hours: int = 24):
    """Get volume trends from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE_TRUNC('hour', timestamp) as hour,
            exchange_name,
            AVG(volume_24h) as avg_volume,
            AVG(price) as avg_price
        FROM market_data
        WHERE token_id = %s
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND volume_24h IS NOT NULL
        GROUP BY hour, exchange_name
        ORDER BY hour DESC
        """

        cur.execute(query, (token_id, hours))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['hour', 'exchange_name', 'avg_volume', 'avg_price'])
            df['hour'] = pd.to_datetime(df['hour'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching volume trends: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_spread_analysis(token_id: str, hours: int = 24):
    """Get bid-ask spread analysis"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            timestamp,
            exchange_name,
            price,
            bid,
            ask,
            CASE
                WHEN bid > 0 AND ask > 0 THEN ((ask - bid) / bid * 100)
                ELSE NULL
            END as spread_percentage
        FROM market_data
        WHERE token_id = %s
            AND timestamp > NOW() - INTERVAL '%s hours'
            AND bid IS NOT NULL
            AND ask IS NOT NULL
        ORDER BY timestamp DESC
        """

        cur.execute(query, (token_id, hours))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['timestamp', 'exchange_name', 'price', 'bid', 'ask', 'spread_percentage'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching spread analysis: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def calculate_volatility(df: pd.DataFrame, window: int = 24):
    """Calculate rolling volatility"""
    if df.empty or 'price' not in df.columns:
        return df

    # Calculate returns
    df = df.sort_values('timestamp')
    df['returns'] = df.groupby('exchange')['price'].pct_change()

    # Calculate rolling standard deviation (volatility)
    df['volatility'] = df.groupby('exchange')['returns'].transform(
        lambda x: x.rolling(window=window, min_periods=1).std() * 100
    )

    return df


def market_page():
    """Display market monitoring page"""
    st.title("💹 Market Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Get latest market data
    market_data = make_api_request(
        f"{settings.EXCHANGE_MONITOR_URL}/api/market/latest/{token_id}"
    )

    if market_data and market_data.get('markets'):
        st.markdown("### 📊 Current Market Data")

        markets_df = pd.DataFrame(market_data['markets'])

        st.dataframe(markets_df, width='stretch')

        # Current metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_price = markets_df['price'].mean() if 'price' in markets_df.columns else 0
            st.metric("Avg Price", f"${avg_price:.6f}")
        with col2:
            if 'volume_24h' in markets_df.columns:
                total_vol = markets_df['volume_24h'].sum()
                st.metric("24h Volume", f"${total_vol:,.0f}")
        with col3:
            if 'high_24h' in markets_df.columns and 'low_24h' in markets_df.columns:
                high = markets_df['high_24h'].max()
                low = markets_df['low_24h'].min()
                volatility = ((high - low) / low * 100) if low > 0 else 0
                st.metric("24h Range", f"{volatility:.2f}%")
        with col4:
            num_exchanges = len(markets_df)
            st.metric("Exchanges", num_exchanges)

        # Price comparison chart
        if not markets_df.empty and 'price' in markets_df.columns:
            fig = px.bar(
                markets_df,
                x='exchange',
                y='price',
                title='Price Comparison Across Exchanges',
                color='price',
                color_continuous_scale='Blues'
            )

            fig.update_layout(
                xaxis_title="Exchange",
                yaxis_title="Price (USD)",
                showlegend=False
            )

            st.plotly_chart(fig, width='stretch')

        st.markdown("---")

        # Volume Distribution
        if 'volume_24h' in markets_df.columns and markets_df['volume_24h'].sum() > 0:
            st.markdown("### 📊 Exchange Volume Distribution")

            col1, col2 = st.columns(2)

            with col1:
                # Pie chart
                fig = px.pie(
                    markets_df,
                    values='volume_24h',
                    names='exchange',
                    title='Volume Share by Exchange',
                    hole=0.4
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, width='stretch')

            with col2:
                # Bar chart
                fig = px.bar(
                    markets_df.sort_values('volume_24h', ascending=True),
                    x='volume_24h',
                    y='exchange',
                    orientation='h',
                    title='Volume by Exchange',
                    labels={'volume_24h': 'Volume (USD)', 'exchange': 'Exchange'}
                )
                st.plotly_chart(fig, width='stretch')

            st.markdown("---")

        # Price History
        st.markdown("### 📈 Price History & Analysis")

        # Time range selector
        col1, col2 = st.columns([3, 1])
        with col2:
            hours = st.selectbox("Time Range", [6, 12, 24, 48, 168], index=2, format_func=lambda x: f"{x}h")

        market_history = make_api_request(
            f"{settings.EXCHANGE_MONITOR_URL}/api/market/history/{token_id}?hours={hours}"
        )

        if market_history and market_history.get('data'):
            df = pd.DataFrame(market_history['data'])

            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Price history line chart
                fig = px.line(
                    df,
                    x='timestamp',
                    y='price',
                    color='exchange',
                    title=f'Price History (Last {hours}h)'
                )

                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Price (USD)",
                    hovermode='x unified',
                    legend_title="Exchange"
                )

                st.plotly_chart(fig, width='stretch')

                # Volatility Analysis
                st.markdown("### 📉 Volatility Analysis")

                df_with_vol = calculate_volatility(df)

                if 'volatility' in df_with_vol.columns:
                    fig = px.line(
                        df_with_vol,
                        x='timestamp',
                        y='volatility',
                        color='exchange',
                        title='Price Volatility (Rolling Std Dev %)'
                    )

                    fig.update_layout(
                        xaxis_title="Time",
                        yaxis_title="Volatility (%)",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, width='stretch')

                    # Volatility stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_vol = df_with_vol['volatility'].mean()
                        st.metric("Avg Volatility", f"{avg_vol:.2f}%")
                    with col2:
                        max_vol = df_with_vol['volatility'].max()
                        st.metric("Max Volatility", f"{max_vol:.2f}%")
                    with col3:
                        current_vol = df_with_vol.groupby('exchange')['volatility'].last().mean()
                        st.metric("Current Volatility", f"{current_vol:.2f}%")

        st.markdown("---")

        # Volume Trends
        st.markdown("### 📊 Volume Trends")

        volume_data = get_volume_trends(token_id, hours)

        if not volume_data.empty:
            fig = px.area(
                volume_data,
                x='hour',
                y='avg_volume',
                color='exchange_name',
                title=f'Trading Volume Trends (Last {hours}h)',
                labels={'hour': 'Time', 'avg_volume': 'Volume', 'exchange_name': 'Exchange'}
            )

            fig.update_layout(hovermode='x unified')
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No volume trend data available")

        st.markdown("---")

        # Bid-Ask Spread Analysis
        st.markdown("### 💰 Bid-Ask Spread Analysis")

        spread_data = get_spread_analysis(token_id, hours)

        if not spread_data.empty and 'spread_percentage' in spread_data.columns:
            # Filter out None/NaN values
            spread_data_clean = spread_data.dropna(subset=['spread_percentage'])

            if not spread_data_clean.empty:
                fig = px.scatter(
                    spread_data_clean,
                    x='timestamp',
                    y='spread_percentage',
                    color='exchange_name',
                    title=f'Bid-Ask Spread Over Time (Last {hours}h)',
                    labels={'timestamp': 'Time', 'spread_percentage': 'Spread %', 'exchange_name': 'Exchange'}
                )

                fig.update_layout(hovermode='x unified')
                st.plotly_chart(fig, width='stretch')

                # Spread statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_spread = spread_data_clean['spread_percentage'].mean()
                    st.metric("Avg Spread", f"{avg_spread:.4f}%")
                with col2:
                    min_spread = spread_data_clean['spread_percentage'].min()
                    st.metric("Min Spread", f"{min_spread:.4f}%")
                with col3:
                    max_spread = spread_data_clean['spread_percentage'].max()
                    st.metric("Max Spread", f"{max_spread:.4f}%")
            else:
                st.info("No valid spread data available")
        else:
            st.info("Spread data not available (requires bid/ask prices)")
    else:
        st.info("No market data available")
