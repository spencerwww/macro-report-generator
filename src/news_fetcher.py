import os
import sys
from tavily import TavilyClient

DEFAULT_QUERIES = [
    "US Federal Reserve monetary policy interest rates latest",
    "Brent crude oil WTI price outlook today",
    "S&P 500 stock market outlook today",
    "geopolitical risk conflict global markets latest",
    "Bitcoin Ethereum cryptocurrency price today",
    "EUR USD GBP USD forex market today",
    "gold price inflation outlook today",
    "corporate earnings results today",
    "IMF World Bank global growth outlook",
    "central bank rate decisions hikes cuts",
    "US CPI PPI inflation data latest",
    "natural gas TTF Henry Hub price today",
]


def fetch_news(queries: list = None) -> list:
    """
    Run Tavily searches for each query. Returns list of result dicts,
    each with query, title, content, url, and published_date fields.
    """
    if queries is None:
        queries = DEFAULT_QUERIES

    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = []

    for query in queries:
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_published_date=True,
            )
            for item in response.get("results", []):
                results.append({
                    "query": query,
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                    "published_date": item.get("published_date", ""),
                })
        except Exception as e:
            print(f"[news_fetcher] WARNING: failed query '{query}': {e}", file=sys.stderr)
            continue

    return results
