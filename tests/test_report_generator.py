import pytest
from unittest.mock import patch, MagicMock
import os
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


ENV = {"ANTHROPIC_API_KEY": "test-key"}


def test_generate_report_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT\n\nTest content")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            result = generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_uses_claude_sonnet():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_generate_report_uses_prompt_caching():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
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
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "2026-04-16" in user_content


def test_system_prompt_preserves_date_placeholder_for_caching():
    """System prompt must keep {DATE} as a literal so it stays static and cache-hits fire."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    system_text = call_kwargs["system"][0]["text"]
    assert "{DATE}" in system_text, "System prompt must contain literal {DATE} for prompt caching"
    assert "2026-04-16" not in system_text, "Resolved date must NOT appear in system prompt"


def test_resolved_date_appears_in_user_message_not_system():
    """Date substitution must happen in the user message, not the system prompt."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("report_generator.anthropic.Anthropic", return_value=mock_client):
        with patch.dict(os.environ, ENV):
            generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "2026-04-16" in user_content
    assert "12:00" in user_content
