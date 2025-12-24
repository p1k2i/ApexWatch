"""
Utility functions for dashboard pages
"""
import streamlit as st
import requests
from config import settings


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
