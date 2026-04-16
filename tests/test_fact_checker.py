import pytest
import os
from unittest.mock import patch, MagicMock
from fact_checker import fact_check

SAMPLE_REPORT = """# MACRO REPORT — 2026-04-16

## EXECUTIVE SUMMARY
S&P 500 at 6,967.38, up 1.18%. Brent crude at $94.79. [Source: https://yahoo.com]
"""

SAMPLE_BUNDLE = {
    "date": "2026-04-16",
    "prices": {
        "equities": {"SP500": {"value": 6967.38, "change_pct": 1.18}},
        "commodities": {"BRENT": {"value": 94.79}},
    },
    "macro": {},
    "news": [],
}

FACT_CHECK_RESPONSE = """## FACT-CHECK & INSIGHTS

### Verified
- S&P 500 at 6,967.38 (+1.18%): confirmed via Yahoo Finance (^GSPC)

### Disputed
- None identified.

### Additional Insights
- VIX at recent lows suggests complacency risk ahead of key catalysts.
"""

ENV = {"ANTHROPIC_API_KEY": "test-key"}


def test_fact_check_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("fact_checker.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert isinstance(result, str)


def test_fact_check_appends_to_original_report():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("fact_checker.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert SAMPLE_REPORT.strip() in result
    assert "## FACT-CHECK & INSIGHTS" in result


def test_fact_check_contains_three_subsections():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("fact_checker.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert "### Verified" in result
    assert "### Disputed" in result
    assert "### Additional Insights" in result


def test_fact_check_uses_prompt_caching():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("fact_checker.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert any(
        isinstance(s, dict) and s.get("cache_control") == {"type": "ephemeral"}
        for s in system
    )
