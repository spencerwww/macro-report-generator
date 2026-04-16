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


def fetch_news(queries: list[str] = None) -> list[dict]:
    """
    Run Tavily searches for each query. Returns list of result dicts,
    each with query, title, content, url, and published_date fields.
    """
    if queries is None:
        queries = DEFAULT_QUERIES

    # Guard TAVILY_API_KEY before TavilyClient instantiation
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("[news_fetcher] WARNING: TAVILY_API_KEY is not set — returning empty news bundle", file=sys.stderr)
        return []

    client = TavilyClient(api_key=api_key)
    seen_urls: set = set()
    results = []

    for query in queries:
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                topic="news",
                days=3,
            )
            for item in response.get("results", []):
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append({
                    "query": query,
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": url,
                    "published_date": item.get("published_date", ""),
                })
        except Exception as e:
            print(f"[news_fetcher] WARNING: failed query '{query}': {e}", file=sys.stderr)
            continue

    return results
