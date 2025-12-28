"""
ApexWatch Dashboard
Streamlit-based dashboard for monitoring and configuration
"""
import streamlit as st

# Page config - MUST be first Streamlit command
st.set_page_config(
    page_title="ApexWatch Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now import everything else
from streamlit_cookies_manager import CookieManager
from auth import verify_token
from page_modules import login_page, overview_page, wallets_page, market_page, news_page, thoughts_page, settings_page, analytics_page
from style_loader import StyleLoader

# Initialize cookies manager
cookies = CookieManager()

# Initialize style loader
style_loader = StyleLoader()


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

    # Restore authentication from cookies (only if cookies are ready)
    if cookies.ready() and not st.session_state.authenticated and 'apexwatch_token' in cookies:
        token = cookies['apexwatch_token']
        # Verify token is still valid
        user_data = verify_token(token)
        if user_data:
            st.session_state.authenticated = True
            st.session_state.username = user_data.get('sub')
            st.session_state.token = token


def apply_sidebar_styles():
    """Apply custom CSS for professional sidebar styling"""
    style_loader.apply_css("sidebar.css")


def main():
    """Main application"""
    # Wait for cookies to be ready
    if not cookies.ready():
        st.stop()

    init_session_state()

    # Check authentication
    if not st.session_state.authenticated:
        login_page(cookies)
        return

    # Apply custom styling
    apply_sidebar_styles()

    # Sidebar
    with st.sidebar:
        # App branding
        st.markdown('<div class="app-title">🔍 ApexWatch</div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle">Real-time Market Intelligence</div>', unsafe_allow_html=True)

        # User info card
        st.markdown(f"""
            <div class="user-card">
                <div class="user-label">Logged in as</div>
                <div class="user-name">{st.session_state.username}</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation section
        st.markdown('<div class="nav-title">Navigation</div>', unsafe_allow_html=True)
        page = st.radio(
            "Navigation",
            ["Overview", "Analytics", "Wallets", "Market", "News", "AI Thoughts", "Settings"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
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
    elif page == "Analytics":
        analytics_page()
    elif page == "Wallets":
        wallets_page()
    elif page == "Market":
        market_page()
    elif page == "News":
        news_page()
    elif page == "AI Thoughts":
        thoughts_page()
    elif page == "Settings":
        settings_page()


if __name__ == "__main__":
    main()
