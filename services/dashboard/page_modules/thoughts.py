"""
AI Thoughts browsing page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
from config import settings
from page_modules.utils import make_api_request


def thoughts_page():
    """Display AI thoughts browsing page"""
    st.title("💭 AI Thoughts")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        limit = st.selectbox("Show", [10, 25, 50, 100], index=2)

    with col2:
        event_types = ["All", "market_update", "news_article", "whale_activity", "price_alert"]
        event_filter = st.selectbox("Event Type", event_types)

    with col3:
        sort_order = st.selectbox("Sort", ["Newest First", "Oldest First"])

    # Get thoughts data
    params = f"?limit={limit}"
    if event_filter != "All":
        params += f"&event_type={event_filter}"

    thoughts_data = make_api_request(
        f"{settings.CORE_SERVICE_URL}/api/thoughts/{token_id}{params}"
    )

    if thoughts_data and thoughts_data.get('thoughts'):
        thoughts = thoughts_data['thoughts']

        # Sort based on selection
        if sort_order == "Oldest First":
            thoughts = thoughts[::-1]

        st.subheader(f"🤖 AI Thoughts ({len(thoughts)} entries)")

        # Display thoughts
        for i, thought in enumerate(thoughts, 1):
            with st.expander(f"#{i} - {thought['event_type']} | {thought['timestamp'][:19]}"):
                # Thought content
                st.markdown("### 💡 Analysis")
                st.write(thought['thought'])

                # Metadata section
                st.markdown("---")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.caption(f"**Model:** {thought['model_used']}")
                    st.caption(f"**Tokens Used:** {thought['tokens_used']}")

                with col2:
                    st.caption(f"**Event Type:** {thought['event_type']}")
                    st.caption(f"**Timestamp:** {thought['timestamp'][:19]}")

                with col3:
                    if thought.get('event_data'):
                        st.caption("**Has Event Data:** ✓")
                    else:
                        st.caption("**Has Event Data:** ✗")

                # Show event data if available
                if thought.get('event_data'):
                    with st.expander("📋 Event Data Details"):
                        st.json(thought['event_data'])

        # Statistics
        st.markdown("---")
        st.subheader("📊 Statistics")

        # Calculate stats
        df = pd.DataFrame(thoughts)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Thoughts", len(thoughts))

        with col2:
            avg_tokens = df['tokens_used'].mean() if 'tokens_used' in df else 0
            st.metric("Avg Tokens", f"{avg_tokens:.0f}")

        with col3:
            total_tokens = df['tokens_used'].sum() if 'tokens_used' in df else 0
            st.metric("Total Tokens", f"{total_tokens:,.0f}")

        with col4:
            unique_events = df['event_type'].nunique() if 'event_type' in df else 0
            st.metric("Event Types", unique_events)

        # Event type distribution
        if 'event_type' in df:
            st.markdown("### Event Type Distribution")
            event_counts = df['event_type'].value_counts()
            st.bar_chart(event_counts)
    else:
        st.info("No AI thoughts available for this token")

