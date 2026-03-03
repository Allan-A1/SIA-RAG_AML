# backend/web/client.py
import requests
from typing import List, Dict
from backend.config.settings import settings


def web_search(query: str, k: int = None) -> List[Dict]:
    """
    Fetch raw web search results.
    Returns raw JSON-like dicts.
    """
    if not settings.search_api_key or not settings.search_endpoint:
        raise RuntimeError("Search API not configured. Set SEARCH_API_KEY and SEARCH_ENDPOINT in .env")

    k = k or settings.web_search_max_results

    response = requests.get(
        settings.search_endpoint,
        params={
            "q": query,
            "num": k,
            "api_key": settings.search_api_key,
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json().get("results", [])
