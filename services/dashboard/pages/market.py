"""
Market monitoring page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from config import settings
from .utils import make_api_request


def market_page():
    """Display market monitoring page"""
    st.title("💹 Market Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Get latest market data
    market_data = make_api_request(
        f"{settings.EXCHANGE_MONITOR_URL}/api/market/latest/{token_id}"
    )

    if market_data and market_data.get('markets'):
        st.subheader("📊 Current Market Data")

        markets_df = pd.DataFrame(market_data['markets'])

        st.dataframe(markets_df, use_container_width=True)

        # Price comparison chart
        if not markets_df.empty and 'price' in markets_df.columns:
            fig = px.bar(
                markets_df,
                x='exchange',
                y='price',
                title='Price Comparison Across Exchanges',
                color='price'
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("📈 Extended Price History")

        # Time range selector
        hours = st.selectbox("Time Range", [6, 12, 24, 48, 168], index=2)

        market_history = make_api_request(
            f"{settings.EXCHANGE_MONITOR_URL}/api/market/history/{token_id}?hours={hours}"
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
                    title=f'{hours}h Price History'
                )

                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No market data available")
