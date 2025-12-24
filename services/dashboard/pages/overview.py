"""
Overview page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from config import settings
from .utils import make_api_request, get_tokens


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
    st.markdown("### System Overview")

    # Get tokens
    tokens = get_tokens()

    if not tokens:
        st.warning("No tokens configured")
        return

    # Token selector
    token_options = {f"{t['symbol']} - {t['name']}": t['id'] for t in tokens}
    selected = st.selectbox("Select Token", list(token_options.keys()))

    if selected:
        token_id = token_options[selected]
        st.session_state.selected_token = token_id

        # Get queue status
        queue_data = make_api_request(f"{settings.CORE_SERVICE_URL}/api/queue/status")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Queue Size", queue_data.get('queue_size', 0) if queue_data else 0)

        with col2:
            # Get market data
            market_data = make_api_request(
                f"{settings.EXCHANGE_MONITOR_URL}/api/market/latest/{token_id}"
            )
            if market_data and market_data.get('markets'):
                avg_price = sum(m['price'] for m in market_data['markets'] if m['price']) / len(market_data['markets'])
                st.metric("Avg Price", f"${avg_price:.4f}")
            else:
                st.metric("Avg Price", "N/A")

        with col3:
            # Get wallet count
            wallet_data = make_api_request(
                f"{settings.WALLET_MONITOR_URL}/api/wallets/summary/{token_id}"
            )
            if wallet_data:
                st.metric("Watched Wallets", wallet_data.get('watched_wallets_count', 0))
            else:
                st.metric("Watched Wallets", 0)

        with col4:
            # Get news count
            news_data = make_api_request(
                f"{settings.NEWS_MONITOR_URL}/api/news/recent/{token_id}?limit=100"
            )
            if news_data:
                st.metric("Recent News", news_data.get('count', 0))
            else:
                st.metric("Recent News", 0)

        st.markdown("---")

        # Two columns for charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Price History")
            display_price_chart(token_id)

        with col2:
            st.subheader("💭 Recent AI Thoughts")
            display_thoughts(token_id)
