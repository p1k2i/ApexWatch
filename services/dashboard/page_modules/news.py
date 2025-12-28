"""
News monitoring page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import settings
from page_modules.utils import make_api_request
from database import get_db_connection


@st.cache_data(ttl=300)
def get_sentiment_distribution(token_id: str):
    """Get sentiment score distribution"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT sentiment_score
        FROM news_articles
        WHERE token_id = %s
            AND sentiment_score IS NOT NULL
            AND published_at > NOW() - INTERVAL '30 days'
        """

        cur.execute(query, (token_id,))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['sentiment_score'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching sentiment distribution: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_sentiment_timeline(token_id: str, days: int = 30):
    """Get sentiment over time"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE(published_at) as date,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as article_count,
            SUM(CASE WHEN sentiment_score > 0.1 THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_score < -0.1 THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_score BETWEEN -0.1 AND 0.1 THEN 1 ELSE 0 END) as neutral_count
        FROM news_articles
        WHERE token_id = %s
            AND published_at > NOW() - INTERVAL '%s days'
            AND sentiment_score IS NOT NULL
        GROUP BY DATE(published_at)
        ORDER BY date DESC
        """

        cur.execute(query, (token_id, days))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['date', 'avg_sentiment', 'article_count', 'positive_count', 'negative_count', 'neutral_count'])
            df['date'] = pd.to_datetime(df['date'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching sentiment timeline: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_sentiment_vs_price(token_id: str, days: int = 30):
    """Get sentiment and price correlation data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE(na.published_at) as date,
            AVG(na.sentiment_score) as avg_sentiment,
            AVG(md.price) as avg_price
        FROM news_articles na
        LEFT JOIN market_data md ON md.token_id = na.token_id
            AND DATE(md.timestamp) = DATE(na.published_at)
        WHERE na.token_id = %s
            AND na.published_at > NOW() - INTERVAL '%s days'
            AND na.sentiment_score IS NOT NULL
        GROUP BY DATE(na.published_at)
        ORDER BY date DESC
        """

        cur.execute(query, (token_id, days))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['date', 'avg_sentiment', 'avg_price'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna()
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching sentiment vs price: {e}")
        return pd.DataFrame()


def news_page():
    """Display news monitoring page"""
    st.title("📰 News Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Sentiment Analytics Section
    st.markdown("### 📊 Sentiment Analytics")

    col1, col2 = st.columns([3, 1])
    with col2:
        sentiment_days = st.selectbox("Time Period", [7, 14, 30, 60], format_func=lambda x: f"{x} days", index=2, key="sentiment_period")

    sentiment_timeline = get_sentiment_timeline(token_id, sentiment_days)

    if not sentiment_timeline.empty:
        # Dual-axis chart: Sentiment + Article Count
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sentiment_timeline['date'],
            y=sentiment_timeline['avg_sentiment'],
            name='Avg Sentiment',
            mode='lines+markers',
            line=dict(color='#2E86DE', width=3),
            yaxis='y'
        ))

        fig.add_trace(go.Bar(
            x=sentiment_timeline['date'],
            y=sentiment_timeline['article_count'],
            name='Article Count',
            marker_color='rgba(84, 160, 255, 0.3)',
            yaxis='y2'
        ))

        fig.update_layout(
            title=f'Sentiment Timeline (Last {sentiment_days} days)',
            xaxis=dict(title='Date'),
            yaxis=dict(
                title='Average Sentiment',
                side='left',
                range=[-1, 1]
            ),
            yaxis2=dict(
                title='Article Count',
                side='right',
                overlaying='y'
            ),
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig, width='stretch')

        # Sentiment composition over time
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=sentiment_timeline['date'],
            y=sentiment_timeline['positive_count'],
            name='Positive',
            mode='lines',
            stackgroup='one',
            fillcolor='rgba(46, 213, 115, 0.5)',
            line=dict(width=0)
        ))

        fig.add_trace(go.Scatter(
            x=sentiment_timeline['date'],
            y=sentiment_timeline['neutral_count'],
            name='Neutral',
            mode='lines',
            stackgroup='one',
            fillcolor='rgba(255, 195, 18, 0.5)',
            line=dict(width=0)
        ))

        fig.add_trace(go.Scatter(
            x=sentiment_timeline['date'],
            y=sentiment_timeline['negative_count'],
            name='Negative',
            mode='lines',
            stackgroup='one',
            fillcolor='rgba(235, 77, 75, 0.5)',
            line=dict(width=0)
        ))

        fig.update_layout(
            title='Sentiment Distribution Over Time',
            xaxis_title='Date',
            yaxis_title='Article Count',
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig, width='stretch')

        # Sentiment statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_sent = float(sentiment_timeline['avg_sentiment'].mean())
            sent_label = "Positive" if avg_sent > 0.1 else "Negative" if avg_sent < -0.1 else "Neutral"
            st.metric("Overall Sentiment", sent_label, f"{avg_sent:.3f}")
        with col2:
            total_articles = sentiment_timeline['article_count'].sum()
            st.metric("Total Articles", int(total_articles))
        with col3:
            positive_pct = (sentiment_timeline['positive_count'].sum() / total_articles * 100) if total_articles > 0 else 0
            st.metric("Positive %", f"{positive_pct:.1f}%")
        with col4:
            negative_pct = (sentiment_timeline['negative_count'].sum() / total_articles * 100) if total_articles > 0 else 0
            st.metric("Negative %", f"{negative_pct:.1f}%")
    else:
        st.info("No sentiment timeline data available")

    st.markdown("---")

    # Sentiment Distribution Histogram
    st.markdown("### 📊 Sentiment Score Distribution")

    sentiment_dist = get_sentiment_distribution(token_id)

    if not sentiment_dist.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Histogram
            fig = px.histogram(
                sentiment_dist,
                x='sentiment_score',
                nbins=50,
                title='Sentiment Score Distribution',
                labels={'sentiment_score': 'Sentiment Score', 'count': 'Frequency'},
                color_discrete_sequence=['#5F27CD']
            )

            fig.update_layout(
                xaxis_title='Sentiment Score',
                yaxis_title='Article Count',
                showlegend=False
            )

            st.plotly_chart(fig, width='stretch')

        with col2:
            # Box plot
            fig = px.box(
                sentiment_dist,
                y='sentiment_score',
                title='Sentiment Score Statistics',
                labels={'sentiment_score': 'Sentiment Score'}
            )

            fig.update_traces(marker_color='#00D2D3', boxmean='sd')
            st.plotly_chart(fig, width='stretch')

        # Statistics
        col1, col2, col3 = st.columns(3)
        # Convert sentiment_score to float to handle Decimal types
        sentiment_scores = sentiment_dist['sentiment_score'].astype(float)
        with col1:
            median_sent = sentiment_scores.median()
            st.metric("Median Sentiment", f"{median_sent:.3f}")
        with col2:
            std_sent = sentiment_scores.std()
            st.metric("Std Deviation", f"{std_sent:.3f}")
        with col3:
            range_sent = sentiment_scores.max() - sentiment_scores.min()
            st.metric("Range", f"{range_sent:.3f}")
    else:
        st.info("No sentiment distribution data available")

    st.markdown("---")

    # Sentiment vs Price Correlation
    st.markdown("### 💹 Sentiment vs Price Correlation")

    corr_data = get_sentiment_vs_price(token_id, sentiment_days)

    if not corr_data.empty and len(corr_data) > 1:
        # Normalize data for dual-axis visualization
        fig = go.Figure()

        # Sentiment line
        fig.add_trace(go.Scatter(
            x=corr_data['date'],
            y=corr_data['avg_sentiment'],
            name='Sentiment',
            mode='lines+markers',
            line=dict(color='#FF6B6B', width=3),
            yaxis='y'
        ))

        # Price line
        fig.add_trace(go.Scatter(
            x=corr_data['date'],
            y=corr_data['avg_price'],
            name='Price',
            mode='lines+markers',
            line=dict(color='#4ECDC4', width=3),
            yaxis='y2'
        ))

        fig.update_layout(
            title='Sentiment vs Price Trend',
            xaxis=dict(title='Date'),
            yaxis=dict(
                title='Sentiment Score',
                side='left',
                range=[-1, 1]
            ),
            yaxis2=dict(
                title='Price (USD)',
                side='right',
                overlaying='y'
            ),
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )

        st.plotly_chart(fig, width='stretch')

        # Correlation scatter
        if 'avg_sentiment' in corr_data.columns and 'avg_price' in corr_data.columns:
            corr_data_clean = corr_data.dropna(subset=['avg_sentiment', 'avg_price'])

            if len(corr_data_clean) > 2:
                fig = px.scatter(
                    corr_data_clean,
                    x='avg_sentiment',
                    y='avg_price',
                    title='Sentiment vs Price Scatter',
                    labels={'avg_sentiment': 'Sentiment Score', 'avg_price': 'Price (USD)'},
                    trendline='ols',
                    hover_data=['date']
                )

                st.plotly_chart(fig, width='stretch')

                # Calculate correlation
                correlation = corr_data_clean['avg_sentiment'].corr(corr_data_clean['avg_price'])

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Correlation Coefficient", f"{correlation:.3f}",
                             help="Pearson correlation between sentiment and price")
                with col2:
                    corr_strength = "Strong" if abs(correlation) > 0.7 else "Moderate" if abs(correlation) > 0.4 else "Weak"
                    corr_direction = "Positive" if correlation > 0 else "Negative"
                    st.metric("Relationship", f"{corr_strength} {corr_direction}")
    else:
        st.info("Insufficient data for correlation analysis")

    st.markdown("---")

    # Get recent news
    st.markdown("### 📄 Recent News Articles")

    col1, col2 = st.columns([3, 1])
    with col2:
        article_limit = st.selectbox("Show Articles", [10, 25, 50, 100], index=1, key="article_limit")

    news_data = make_api_request(
        f"{settings.NEWS_MONITOR_URL}/api/news/recent/{token_id}?limit={article_limit}"
    )

    if news_data and news_data.get('articles'):
        st.caption(f"Showing {news_data['count']} articles")

        for article in news_data['articles']:
            with st.expander(f"📰 {article['title']}"):
                st.write(article['summary'])

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Relevance", f"{article['relevance_score']:.2f}")
                with col2:
                    sentiment = article['sentiment_score']
                    if sentiment > 0.1:
                        sentiment_label = "😊 Positive"
                        sentiment_color = "green"
                    elif sentiment < -0.1:
                        sentiment_label = "😞 Negative"
                        sentiment_color = "red"
                    else:
                        sentiment_label = "😐 Neutral"
                        sentiment_color = "gray"
                    st.markdown(f"**Sentiment:** :{sentiment_color}[{sentiment_label}]")
                    st.caption(f"Score: {sentiment:.3f}")
                with col3:
                    st.write(f"**Source:** {article['source']}")
                with col4:
                    st.write(f"**Published:** {article['published_at'][:10]}")

                if article['url']:
                    st.markdown(f"[🔗 Read full article]({article['url']})")
    else:
        st.info("No news articles available")
