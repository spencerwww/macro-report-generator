import pytest
from main import assemble_bundle
# run_pipeline will be imported in Task 9


def test_assemble_bundle_returns_required_keys():
    prices = {"equities": {}, "fx": {}, "crypto": {}, "commodities": {}}
    macro = {"cpi_yoy": {"value": 3.3}}
    news = [{"query": "test", "title": "Test", "content": "...", "url": "https://example.com"}]
    result = assemble_bundle(prices, macro, news)
    assert "date" in result
    assert "timestamp" in result
    assert "prices" in result
    assert "macro" in result
    assert "news" in result


def test_assemble_bundle_date_is_iso_format():
    result = assemble_bundle({}, {}, [])
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["date"])


def test_assemble_bundle_passthrough_unchanged():
    prices = {"equities": {"SP500": {"value": 6967.38}}}
    macro = {"cpi_yoy": {"value": 3.3}}
    news = [{"url": "https://reuters.com"}]
    result = assemble_bundle(prices, macro, news)
    assert result["prices"]["equities"]["SP500"]["value"] == 6967.38
    assert result["macro"]["cpi_yoy"]["value"] == 3.3
    assert result["news"][0]["url"] == "https://reuters.com"
