import pytest
from unittest.mock import patch, MagicMock
from news_fetcher import fetch_news, DEFAULT_QUERIES


def _mock_tavily_client(results=None):
    mock = MagicMock()
    if results is None:
        results = [
            {
                "title": "Test Article",
                "content": "Test content about markets.",
                "url": "https://reuters.com/test",
                "published_date": "2026-04-16",
            }
        ]
    mock.search.return_value = {
        "results": results
    }
    return mock


def test_fetch_news_returns_list():
    with patch("news_fetcher.TavilyClient", return_value=_mock_tavily_client()), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        result = fetch_news(["test query"])
    assert isinstance(result, list)
    assert len(result) > 0


def test_fetch_news_result_has_required_fields():
    with patch("news_fetcher.TavilyClient", return_value=_mock_tavily_client()), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        result = fetch_news(["test query"])
    item = result[0]
    assert "query" in item
    assert "title" in item
    assert "content" in item
    assert "url" in item
    assert "published_date" in item


def test_fetch_news_query_echoed_in_result():
    with patch("news_fetcher.TavilyClient", return_value=_mock_tavily_client()), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        result = fetch_news(["oil price today"])
    assert result[0]["query"] == "oil price today"


def test_fetch_news_handles_tavily_error_gracefully():
    mock = MagicMock()
    mock.search.side_effect = Exception("Tavily API error")
    with patch("news_fetcher.TavilyClient", return_value=mock), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        result = fetch_news(["test query"])
    assert result == []


def test_fetch_news_empty_results_handled():
    with patch("news_fetcher.TavilyClient", return_value=_mock_tavily_client(results=[])), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        result = fetch_news(["test query"])
    assert result == []


def test_default_queries_covers_key_topics():
    topics = " ".join(DEFAULT_QUERIES).lower()
    assert "federal reserve" in topics or "fed" in topics
    assert "oil" in topics or "brent" in topics
    assert "bitcoin" in topics or "crypto" in topics
    assert "inflation" in topics or "cpi" in topics
    assert "gold" in topics


def test_fetch_news_uses_default_queries_when_none_given():
    mock = _mock_tavily_client()
    with patch("news_fetcher.TavilyClient", return_value=mock), \
         patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
        fetch_news()
    assert mock.search.call_count == len(DEFAULT_QUERIES)
