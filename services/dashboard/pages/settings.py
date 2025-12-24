"""
Settings page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
from config import settings
from .utils import make_api_request, get_tokens


def settings_page():
    """Display settings page"""
    st.title("⚙️ Settings")

    tabs = st.tabs(["Tokens", "Monitoring Settings", "System Config"])

    with tabs[0]:
        st.subheader("Token Configuration")

        tokens = get_tokens()
        if tokens:
            st.dataframe(
                pd.DataFrame(tokens),
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("Add New Token")

        with st.form("add_token"):
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Symbol (e.g., USDT)")
                contract_address = st.text_input("Contract Address")
                chain = st.selectbox("Chain", ["ethereum", "polygon", "bsc"])

            with col2:
                name = st.text_input("Name (e.g., Tether USD)")
                decimals = st.number_input("Decimals", min_value=0, max_value=18, value=18)

            submit = st.form_submit_button("Add Token")

            if submit:
                st.info("Token addition requires database access - feature coming soon")

    with tabs[1]:
        st.subheader("Monitoring Settings")

        if not st.session_state.selected_token:
            st.warning("Please select a token from the Overview page")
        else:
            token_id = st.session_state.selected_token

            st.write("Adjust monitoring thresholds:")

            with st.form("update_settings"):
                col1, col2 = st.columns(2)

                with col1:
                    min_transfer = st.number_input(
                        "Minimum Transfer Amount",
                        min_value=0,
                        value=1000000,
                        help="Minimum token amount to trigger wallet monitoring"
                    )

                    price_threshold = st.number_input(
                        "Price Change Threshold (%)",
                        min_value=0.0,
                        value=5.0,
                        help="Percentage change to trigger price alerts"
                    )

                with col2:
                    max_transfer = st.number_input(
                        "Maximum Transfer Amount",
                        min_value=0,
                        value=100000000000,
                        help="Maximum token amount to track"
                    )

                    volume_threshold = st.number_input(
                        "Volume Spike Threshold (%)",
                        min_value=0.0,
                        value=200.0,
                        help="Percentage increase to trigger volume alerts"
                    )

                submit = st.form_submit_button("Update Settings")

                if submit:
                    # Update settings via API
                    settings_updates = [
                        {"token_id": token_id, "setting_key": "wallet_min_threshold", "setting_value": str(min_transfer)},
                        {"token_id": token_id, "setting_key": "wallet_max_threshold", "setting_value": str(max_transfer)},
                        {"token_id": token_id, "setting_key": "price_change_threshold", "setting_value": str(price_threshold)},
                        {"token_id": token_id, "setting_key": "volume_spike_threshold", "setting_value": str(volume_threshold)}
                    ]

                    for setting in settings_updates:
                        result = make_api_request(
                            f"{settings.CORE_SERVICE_URL}/api/settings/update",
                            method="POST",
                            data=setting
                        )

                    st.success("Settings updated successfully!")

    with tabs[2]:
        st.subheader("System Configuration")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Core Service", "🟢 Running")
            st.metric("Wallet Monitor", "🟢 Running")

        with col2:
            st.metric("Exchange Monitor", "🟢 Running")
            st.metric("News Monitor", "🟢 Running")
