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


def test_load_recent_reports_returns_empty_when_dir_missing(tmp_path):
    from main import load_recent_reports
    result = load_recent_reports(reports_dir=str(tmp_path / "nope"), n=2)
    assert result == []


def test_load_recent_reports_returns_last_n_oldest_first(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    for d in ["2026-05-26", "2026-05-27", "2026-05-28", "2026-05-29"]:
        (reports / f"{d}.md").write_text(f"report {d}", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2)
    assert [r["date"] for r in result] == ["2026-05-28", "2026-05-29"]
    assert result[1]["content"] == "report 2026-05-29"


def test_load_recent_reports_excludes_before_date(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    for d in ["2026-05-28", "2026-05-29", "2026-05-30"]:
        (reports / f"{d}.md").write_text(f"report {d}", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2, before_date="2026-05-30")
    assert [r["date"] for r in result] == ["2026-05-28", "2026-05-29"]


def test_load_recent_reports_ignores_non_dated_files(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "README.md").write_text("readme", encoding="utf-8")
    (reports / "2026-05-29.md").write_text("report", encoding="utf-8")
    result = load_recent_reports(reports_dir=str(reports), n=2)
    assert [r["date"] for r in result] == ["2026-05-29"]


def test_load_recent_reports_returns_empty_when_n_zero(tmp_path):
    from main import load_recent_reports
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "2026-05-29.md").write_text("report", encoding="utf-8")
    assert load_recent_reports(reports_dir=str(reports), n=0) == []
