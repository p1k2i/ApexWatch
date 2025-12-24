"""
Wallet monitoring page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
from config import settings
from .utils import make_api_request


def wallets_page():
    """Display wallet monitoring page"""
    st.title("👛 Wallet Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Get wallet summary
    wallet_data = make_api_request(
        f"{settings.WALLET_MONITOR_URL}/api/wallets/summary/{token_id}"
    )

    if wallet_data and wallet_data.get('wallets'):
        st.subheader("🐋 Top Whale Wallets")

        wallets_df = pd.DataFrame(wallet_data['wallets'])

        st.dataframe(
            wallets_df[[
                'address', 'balance', 'is_whale',
                'discovered_automatically', 'last_activity'
            ]],
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("📊 Recent Transactions")

        # Get recent transactions
        tx_data = make_api_request(
            f"{settings.WALLET_MONITOR_URL}/api/transactions/{token_id}?limit=20"
        )

        if tx_data and tx_data.get('transactions'):
            tx_df = pd.DataFrame(tx_data['transactions'])

            st.dataframe(
                tx_df[['timestamp', 'from', 'to', 'amount', 'tx_hash']],
                use_container_width=True
            )
        else:
            st.info("No recent transactions")
    else:
        st.info("No wallets being monitored")
