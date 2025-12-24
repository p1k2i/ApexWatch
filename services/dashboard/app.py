"""
ApexWatch Dashboard
Streamlit-based dashboard for monitoring and configuration
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from config import settings
from auth import authenticate_user, create_access_token, verify_token, get_db_connection
from psycopg2.extras import RealDictCursor
from streamlit_cookies_manager import CookieManager


# Page config
st.set_page_config(
    page_title="ApexWatch Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize cookies manager
cookies = CookieManager()

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'selected_token' not in st.session_state:
        st.session_state.selected_token = None

    # Restore authentication from cookies
    if not st.session_state.authenticated and 'apexwatch_token' in cookies:
        token = cookies['apexwatch_token']
        # Verify token is still valid
        user_data = verify_token(token)
        if user_data:
            st.session_state.authenticated = True
            st.session_state.username = user_data.get('sub')
            st.session_state.token = token


def login_page():
    """Display login page"""
    st.title("🔐 ApexWatch Login")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Please login to continue")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

                    # Store token in cookie for persistence
                    cookies['apexwatch_token'] = token
                    cookies['apexwatch_username'] = username
                    cookies.save()

        if st.button("Login", use_container_width=True):
            if username and password:
                user = authenticate_user(username, password)

                if user:
                    # Create JWT token
                    token = create_access_token({"sub": username})

                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.token = token

                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Please enter both username and password")

        st.markdown("---")
        st.caption("Default credentials: admin / admin123")


def make_api_request(url: str, method: str = "GET", data: dict = None):
    """Make API request with authentication"""
    headers = {"X-Access-Key": settings.ACCESS_KEY}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return None

        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def get_tokens():
    """Get list of tokens"""
    data = make_api_request(f"{settings.CORE_SERVICE_URL}/api/tokens")
    return data.get('tokens', []) if data else []


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


def news_page():
    """Display news monitoring page"""
    st.title("📰 News Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Get recent news
    news_data = make_api_request(
        f"{settings.NEWS_MONITOR_URL}/api/news/recent/{token_id}?limit=50"
    )

    if news_data and news_data.get('articles'):
        st.subheader(f"📄 Recent News ({news_data['count']} articles)")

        for article in news_data['articles']:
            with st.expander(f"📰 {article['title']}"):
                st.write(article['summary'])

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Relevance", f"{article['relevance_score']:.2f}")
                with col2:
                    sentiment = article['sentiment_score']
                    sentiment_label = "Positive" if sentiment > 0.1 else "Negative" if sentiment < -0.1 else "Neutral"
                    st.metric("Sentiment", sentiment_label)
                with col3:
                    st.write(f"**Source:** {article['source']}")
                with col4:
                    st.write(f"**Published:** {article['published_at'][:10]}")

                if article['url']:
                    st.markdown(f"[Read full article]({article['url']})")
    else:
        st.info("No news articles available")


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


def main():
    """Main application"""
    init_session_state()

    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return

    # Sidebar
    with st.sidebar:
        st.title("🔍 ApexWatch")
        st.markdown(f"**User:** {st.session_state.username}")

        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["Overview", "Wallets", "Market", "News", "Settings"]
        )

        st.markdown("---")

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.token = None
            # Clear cookies
            if 'apexwatch_token' in cookies:
                del cookies['apexwatch_token']
            if 'apexwatch_username' in cookies:
                del cookies['apexwatch_username']
            cookies.save()
            st.rerun()

    # Display selected page
    if page == "Overview":
        overview_page()
    elif page == "Wallets":
        wallets_page()
    elif page == "Market":
        market_page()
    elif page == "News":
        news_page()
    elif page == "Settings":
        settings_page()


if __name__ == "__main__":
    main()
