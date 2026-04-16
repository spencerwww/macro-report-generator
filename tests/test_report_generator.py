import pytest
from unittest.mock import patch, MagicMock
from report_generator import generate_report

SAMPLE_BUNDLE = {
    "date": "2026-04-16",
    "timestamp": "2026-04-16T12:00:00+00:00",
    "prices": {
        "equities": {"SP500": {"value": 6967.38, "change_pct": 1.18, "source": "Yahoo Finance (^GSPC)"}},
        "fx": {},
        "crypto": {},
        "commodities": {},
    },
    "macro": {"cpi_yoy": {"value": 3.3, "url": "https://fred.stlouisfed.org/series/CPIAUCSL"}},
    "news": [{"query": "oil", "title": "Oil falls", "content": "Brent down 4%", "url": "https://reuters.com/1"}],
}

SAMPLE_TEMPLATE = "# MACRO REPORT — {DATE}\n\n## 7. ALL-ASSET SUMMARY DASHBOARD\n"


def test_generate_report_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT\n\nTest content")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        result = generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_uses_claude_sonnet():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_generate_report_uses_prompt_caching():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert any(
        isinstance(s, dict) and s.get("cache_control") == {"type": "ephemeral"}
        for s in system
    )


def test_generate_report_includes_bundle_date_in_message():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "2026-04-16" in user_content
