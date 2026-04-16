import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
from main import assemble_bundle, run_pipeline


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


def test_assemble_bundle_does_not_share_references():
    prices = {"equities": {"SP500": {"value": 100.0}}}
    result = assemble_bundle(prices, {}, [])
    prices["equities"]["SP500"]["value"] = 999.0
    assert result["prices"]["equities"]["SP500"]["value"] == 100.0


def test_run_pipeline_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "report_template.md").write_text("# Template")

    with patch("main.fetch_prices", return_value={"equities": {}, "fx": {}, "crypto": {}, "commodities": {}}), \
         patch("main.fetch_macro", return_value={}), \
         patch("main.fetch_news", return_value=[]), \
         patch("main.generate_report", return_value="# MACRO REPORT\n\nContent"), \
         patch("main.fact_check", return_value="# MACRO REPORT\n\nContent\n\n---\n\n## FACT-CHECK"):

        output_path = run_pipeline()

    assert Path(output_path).exists()
    content = Path(output_path).read_text()
    assert "MACRO REPORT" in content
