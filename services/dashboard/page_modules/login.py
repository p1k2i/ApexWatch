"""
Login page for ApexWatch Dashboard
"""
import streamlit as st
from auth import authenticate_user, create_access_token


def login_page(cookies):
    """Display login page"""
    st.title("🔐 ApexWatch Login")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Please login to continue")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", width='stretch')

            if submit:
                if username and password:
                    user = authenticate_user(username, password)

                    if user:
                        # Create JWT token
                        token = create_access_token({"sub": username})

                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.token = token

                        # Store token in cookie for persistence
                        cookies['apexwatch_token'] = token
                        cookies['apexwatch_username'] = username
                        cookies.save()

                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please enter both username and password")

        st.markdown("---")
        st.caption("Default credentials: admin / admin123")
