"""
News monitoring page for ApexWatch Dashboard
"""
import streamlit as st
from config import settings
from .utils import make_api_request


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
