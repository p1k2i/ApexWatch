"""
ApexWatch Dashboard
Streamlit-based dashboard for monitoring and configuration
"""
import streamlit as st
from streamlit_cookies_manager import CookieManager
from auth import verify_token
from pages import login_page, overview_page, wallets_page, market_page, news_page, settings_page


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


def main():
    """Main application"""
    init_session_state()

    # Check authentication
    if not st.session_state.authenticated:
        login_page(cookies)
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
