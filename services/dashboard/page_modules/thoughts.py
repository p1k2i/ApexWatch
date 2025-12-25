"""
AI Thoughts browsing page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import settings
from page_modules.utils import make_api_request


def format_timestamp(ts_str: str) -> str:
    """Format timestamp to a more readable format"""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return ts_str[:19]


def get_event_emoji(event_type: str) -> str:
    """Get emoji for event type"""
    emojis = {
        "market_update": "📊",
        "news_article": "📰",
        "whale_activity": "🐋",
        "price_alert": "🔔",
    }
    return emojis.get(event_type, "💭")


def thoughts_page():
    """Display AI thoughts browsing page with split view"""
    st.title("💭 AI Thoughts Browser")

    if not st.session_state.selected_token:
        st.warning("⚠️ Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Initialize session state for selected thought
    if 'selected_thought_id' not in st.session_state:
        st.session_state.selected_thought_id = None

    # Filters in the top bar
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        limit = st.selectbox("📊 Show", [25, 50, 100, 200], index=1, key="limit_select")

    with col2:
        event_types = ["All", "market_update", "news_article", "whale_activity", "price_alert"]
        event_filter = st.selectbox("🎯 Filter by Type", event_types, key="event_filter")

    with col3:
        sort_order = st.selectbox("🔄 Sort", ["Newest First", "Oldest First"], key="sort_order")

    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # Get thoughts list (minimal data)
    params = f"?limit={limit}"
    if event_filter != "All":
        params += f"&event_type={event_filter}"

    thoughts_data = make_api_request(
        f"{settings.CORE_SERVICE_URL}/api/thoughts/{token_id}/list{params}"
    )

    if not thoughts_data or not thoughts_data.get('thoughts'):
        st.info("📭 No AI thoughts available for this token")
        return

    thoughts = thoughts_data['thoughts']

    # Sort based on selection
    if sort_order == "Oldest First":
        thoughts = thoughts[::-1]

    # Split view layout
    list_col, viewer_col = st.columns([1, 2])

    # Left side - Thought list
    with list_col:
        st.markdown("### 📋 Thoughts List")
        st.caption(f"Showing {len(thoughts)} entries")

        # Scrollable list container
        for i, thought in enumerate(thoughts):
            # Determine if this thought is selected
            is_selected = st.session_state.selected_thought_id == thought['id']

            with st.container():
                # Create button that looks like a list item
                col_emoji, col_content = st.columns([0.1, 0.9])

                with col_emoji:
                    st.markdown(f"<span style='font-size:20px;'>{get_event_emoji(thought['event_type'])}</span>",
                              unsafe_allow_html=True)

                with col_content:
                    # Button to select this thought
                    if st.button(
                        f"{thought['event_type'].replace('_', ' ').title()}",
                        key=f"thought_{thought['id']}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary"
                    ):
                        st.session_state.selected_thought_id = thought['id']
                        st.rerun()

                    # Compact metadata in one line
                    st.caption(f"⏱️ {format_timestamp(thought['timestamp'])[:17]} • 🤖 {thought['model_used'].split('/')[-1][:10]} • {thought['tokens_used']} tokens")

                    # Shorter preview text
                    if thought.get('thought_preview'):
                        preview = thought['thought_preview'].strip()
                        if len(preview) > 60:
                            preview = preview[:60] + "..."
                        st.caption(f"{preview}")

                st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    # Right side - Thought viewer
    with viewer_col:
        if st.session_state.selected_thought_id:
            # Load full thought detail
            thought_detail = make_api_request(
                f"{settings.CORE_SERVICE_URL}/api/thoughts/{token_id}/detail/{st.session_state.selected_thought_id}"
            )

            if thought_detail:
                # Header with metadata
                st.markdown(f"### {get_event_emoji(thought_detail['event_type'])} {thought_detail['event_type'].replace('_', ' ').title()}")

                # Metadata cards
                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

                with meta_col1:
                    st.metric("⏱️ Time", format_timestamp(thought_detail['timestamp'])[:12])

                with meta_col2:
                    st.metric("🤖 Model", thought_detail['model_used'].split('/')[-1][:15])

                with meta_col3:
                    st.metric("🔢 Tokens", f"{thought_detail['tokens_used']:,}")

                with meta_col4:
                    processing_time = thought_detail.get('processing_time_ms', 0)
                    st.metric("⚡ Time", f"{processing_time}ms")

                st.markdown("---")

                # Main thought content
                st.markdown("#### 💡 AI Analysis")
                st.markdown(
                    f"<div style='background-color: #1e1e1e; padding: 20px; border-radius: 8px; "
                    f"border-left: 4px solid #4CAF50; line-height: 1.6;'>"
                    f"{thought_detail['thought']}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                st.markdown("---")

                # Prompt section (collapsible)
                with st.expander("📝 View Prompt"):
                    st.code(thought_detail.get('prompt', 'No prompt available'), language="text")

                # Event ID info
                if thought_detail.get('event_id'):
                    with st.expander("🔍 Technical Details"):
                        st.text(f"Event ID: {thought_detail['event_id']}")
                        st.text(f"Thought ID: {thought_detail['id']}")
                        st.text(f"Token ID: {thought_detail['token_id']}")

            else:
                st.error("❌ Failed to load thought details")

        else:
            # Empty state
            st.markdown(
                "<div style='text-align: center; padding: 100px 20px;'>"
                "<h2 style='color: #888;'>👈 Select a thought from the list</h2>"
                "<p style='color: #666;'>Click on any thought to view its details here</p>"
                "</div>",
                unsafe_allow_html=True
            )

    # Statistics section at the bottom
    st.markdown("---")
    st.markdown("### 📊 Statistics")

    # Calculate stats from the list
    df = pd.DataFrame(thoughts)

    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)

    with stat_col1:
        st.metric("📝 Total Thoughts", len(thoughts))

    with stat_col2:
        avg_tokens = df['tokens_used'].mean() if 'tokens_used' in df and len(df) > 0 else 0
        st.metric("📊 Avg Tokens", f"{avg_tokens:.0f}")

    with stat_col3:
        total_tokens = df['tokens_used'].sum() if 'tokens_used' in df and len(df) > 0 else 0
        st.metric("🔢 Total Tokens", f"{total_tokens:,}")

    with stat_col4:
        unique_events = df['event_type'].nunique() if 'event_type' in df and len(df) > 0 else 0
        st.metric("🎯 Event Types", unique_events)

    with stat_col5:
        avg_time = df['processing_time_ms'].mean() if 'processing_time_ms' in df and len(df) > 0 else 0
        st.metric("⚡ Avg Time", f"{avg_time:.0f}ms")

    # Event type distribution chart
    if 'event_type' in df and len(df) > 0:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### 📈 Event Type Distribution")
            event_counts = df['event_type'].value_counts()
            st.bar_chart(event_counts)

        with col2:
            st.markdown("#### 🎨 Event Types")
            for event_type, count in event_counts.items():
                emoji = get_event_emoji(event_type)
                st.markdown(f"{emoji} **{event_type}**: {count}")


