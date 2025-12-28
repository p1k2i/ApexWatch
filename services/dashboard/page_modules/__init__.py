"""
ApexWatch Dashboard Pages
"""
from .login import login_page
from .overview import overview_page
from .wallets import wallets_page
from .market import market_page
from .news import news_page
from .thoughts import thoughts_page
from .settings import settings_page
from .analytics import analytics_page

__all__ = [
    'login_page',
    'overview_page',
    'wallets_page',
    'market_page',
    'news_page',
    'thoughts_page',
    'settings_page',
    'analytics_page'
]
