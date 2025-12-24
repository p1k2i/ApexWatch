"""
News Monitor
Aggregates news from RSS feeds and analyzes relevance using NLP
"""
import logging
import feedparser
import requests
from typing import Dict, Any, List, Optional
import time
from datetime import datetime, timedelta
from textblob import TextBlob
import re
from config import settings
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class NewsMonitor:
    """Monitors news sources and filters relevant articles"""

    def __init__(self):
        self.db_params = {
            'host': settings.POSTGRES_HOST,
            'port': settings.POSTGRES_PORT,
            'database': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD
        }
        self.processed_urls = set()

    def get_news_sources(self) -> List[Dict[str, Any]]:
        """Get active news sources from database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, name, url, source_type, is_active
                FROM news_sources
                WHERE is_active = TRUE
            """)

            sources = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()

            return sources

        except Exception as e:
            logger.error(f"Error fetching news sources: {e}")
            return []

    def get_token_configs(self) -> List[Dict[str, Any]]:
        """Get token configurations"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT id, symbol, name
                FROM tokens
                WHERE is_active = TRUE
            """)

            tokens = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()

            return tokens

        except Exception as e:
            logger.error(f"Error fetching token configs: {e}")
            return []

    def fetch_rss_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetch articles from RSS feed"""
        try:
            feed = feedparser.parse(url)

            articles = []
            for entry in feed.entries[:20]:  # Limit to 20 most recent
                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'content': entry.get('content', [{}])[0].get('value', '') if entry.get('content') else '',
                    'published': entry.get('published', ''),
                }

                # Skip if already processed
                if article['url'] in self.processed_urls:
                    continue

                articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return []

    def calculate_relevance(self, article: Dict[str, Any], token: Dict[str, Any]) -> float:
        """Calculate relevance score for an article relative to a token"""
        text = f"{article['title']} {article['summary']} {article['content']}"
        text_lower = text.lower()

        # Keywords to search for
        keywords = [
            token['symbol'].lower(),
            token['name'].lower(),
            'crypto', 'cryptocurrency', 'blockchain',
            'bitcoin', 'ethereum', 'defi'
        ]

        # Count keyword occurrences
        score = 0.0
        for keyword in keywords:
            if keyword in text_lower:
                # Symbol or name matches are highly relevant
                if keyword in [token['symbol'].lower(), token['name'].lower()]:
                    score += 0.5
                else:
                    score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            # Returns polarity score between -1 (negative) and 1 (positive)
            return blob.sentiment.polarity
        except Exception as e:
            logger.warning(f"Error analyzing sentiment: {e}")
            return 0.0

    def extract_summary(self, article: Dict[str, Any], max_length: int = 500) -> str:
        """Extract or create a summary"""
        summary = article.get('summary', '')

        if not summary:
            # Use first part of content if no summary
            content = article.get('content', '')
            summary = content[:max_length] + "..." if len(content) > max_length else content
        elif len(summary) > max_length:
            summary = summary[:max_length] + "..."

        # Clean HTML tags
        summary = re.sub(r'<[^>]+>', '', summary)

        return summary

    def store_article(self, token_id: str, source_id: str, article: Dict[str, Any],
                     relevance_score: float, sentiment_score: float):
        """Store article in database"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Parse published date
            published_at = None
            if article.get('published'):
                try:
                    from dateutil import parser as date_parser
                    published_at = date_parser.parse(article['published'])
                except:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()

            summary = self.extract_summary(article)
            is_relevant = relevance_score >= settings.MIN_RELEVANCE_SCORE

            cur.execute("""
                INSERT INTO news_articles
                (token_id, source_id, title, summary, url, content,
                 relevance_score, sentiment_score, published_at, is_relevant)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                token_id, source_id, article['title'], summary,
                article['url'], article.get('content', ''),
                relevance_score, sentiment_score, published_at, is_relevant
            ))

            conn.commit()
            cur.close()
            conn.close()

            # Mark as processed
            self.processed_urls.add(article['url'])

        except Exception as e:
            logger.error(f"Error storing article: {e}")

    def send_event_to_core(self, event: Dict[str, Any]):
        """Send event to Core Service"""
        try:
            response = requests.post(
                f"{settings.CORE_SERVICE_URL}/api/webhook/event",
                json=event,
                headers={"X-Access-Key": settings.ACCESS_KEY},
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Sent news event to Core Service")

        except Exception as e:
            logger.error(f"Failed to send event to Core Service: {e}")

    def process_source(self, source: Dict[str, Any], tokens: List[Dict[str, Any]]):
        """Process a news source for all tokens"""
        source_id = str(source['id'])
        source_name = source['name']

        try:
            # Fetch articles based on source type
            if source['source_type'] == 'rss':
                articles = self.fetch_rss_feed(source['url'])
            else:
                logger.warning(f"Unsupported source type: {source['source_type']}")
                return

            logger.info(f"Fetched {len(articles)} articles from {source_name}")

            # Process each article
            for article in articles:
                for token in tokens:
                    token_id = str(token['id'])

                    # Calculate relevance
                    relevance_score = self.calculate_relevance(article, token)

                    if relevance_score < settings.MIN_RELEVANCE_SCORE:
                        continue  # Skip irrelevant articles

                    # Analyze sentiment
                    text_for_sentiment = f"{article['title']} {article['summary']}"
                    sentiment_score = self.analyze_sentiment(text_for_sentiment)

                    # Store article
                    self.store_article(
                        token_id, source_id, article,
                        relevance_score, sentiment_score
                    )

                    # Send event to Core Service
                    self.send_event_to_core({
                        'type': 'news_update',
                        'data': {
                            'token_id': token_id,
                            'title': article['title'],
                            'summary': self.extract_summary(article),
                            'source': source_name,
                            'url': article['url'],
                            'relevance_score': round(relevance_score, 2),
                            'sentiment_score': round(sentiment_score, 2),
                            'published_at': article.get('published', datetime.now().isoformat())
                        }
                    })

                    logger.info(f"Relevant article for {token['symbol']}: {article['title'][:50]}...")

        except Exception as e:
            logger.error(f"Error processing source {source_name}: {e}")

    def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting news monitoring loop...")

        while True:
            try:
                # Get sources and tokens
                sources = self.get_news_sources()
                tokens = self.get_token_configs()

                if not sources:
                    logger.warning("No news sources configured")
                elif not tokens:
                    logger.warning("No tokens configured")
                else:
                    # Process each source
                    for source in sources:
                        self.process_source(source, tokens)

                # Wait before next iteration
                time.sleep(settings.POLL_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)


# Global monitor instance
news_monitor = NewsMonitor()
