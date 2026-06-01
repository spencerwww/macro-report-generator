import pytest
from unittest.mock import patch, MagicMock
from email_sender import render_html


SAMPLE_MD = """# Daily Macro Report

## 1. Executive Summary

Markets were mixed today.

## 8. All-Asset Summary Dashboard

| Asset | Price | Change |
|-------|-------|--------|
| S&P 500 | 5200 | +0.5% |
| Gold | 2350 | -0.2% |
"""


def test_render_html_returns_full_document():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "</html>" in html


def test_render_html_converts_table_to_html_table():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "<table>" in html
    assert "<td>S&amp;P 500</td>" in html


def test_render_html_includes_report_date_in_title():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "<title>Macro Report — 2026-06-01</title>" in html


def test_render_html_includes_heading_content():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "Executive Summary" in html
    assert "Markets were mixed today." in html


def test_render_html_includes_inline_style_block():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "<style>" in html
    assert "table" in html  # table styling present


def _env(**overrides):
    base = {
        "RESEND_API_KEY": "re_test_key",
        "REPORT_RECIPIENT_EMAIL": "me@example.com",
        "RESEND_FROM": "onboarding@resend.dev",
    }
    base.update(overrides)
    return base


def test_send_report_posts_to_resend_and_returns_true(tmp_path):
    report = tmp_path / "2026-06-01.md"
    report.write_text(SAMPLE_MD, encoding="utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("email_sender.requests.post", return_value=mock_resp) as mock_post, \
         patch.dict("os.environ", _env(), clear=True):
        from email_sender import send_report
        result = send_report(str(report))

    assert result is True
    assert mock_post.call_count == 1
    args, kwargs = mock_post.call_args
    assert "api.resend.com" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    payload = kwargs["json"]
    assert payload["to"] == "me@example.com"
    assert payload["from"] == "onboarding@resend.dev"
    assert payload["subject"] == "Macro Report — 2026-06-01"
    assert "<table>" in payload["html"]


def test_send_report_returns_false_when_api_key_missing(tmp_path):
    report = tmp_path / "2026-06-01.md"
    report.write_text(SAMPLE_MD, encoding="utf-8")
    with patch("email_sender.requests.post") as mock_post, \
         patch.dict("os.environ", _env(RESEND_API_KEY=""), clear=True):
        from email_sender import send_report
        result = send_report(str(report))
    assert result is False
    assert mock_post.call_count == 0


def test_send_report_returns_false_when_recipient_missing(tmp_path):
    report = tmp_path / "2026-06-01.md"
    report.write_text(SAMPLE_MD, encoding="utf-8")
    with patch("email_sender.requests.post") as mock_post, \
         patch.dict("os.environ", _env(REPORT_RECIPIENT_EMAIL=""), clear=True):
        from email_sender import send_report
        result = send_report(str(report))
    assert result is False
    assert mock_post.call_count == 0


def test_send_report_returns_false_on_missing_file():
    with patch("email_sender.requests.post") as mock_post, \
         patch.dict("os.environ", _env(), clear=True):
        from email_sender import send_report
        result = send_report("reports/does-not-exist.md")
    assert result is False
    assert mock_post.call_count == 0


def test_send_report_returns_false_on_non_2xx(tmp_path):
    report = tmp_path / "2026-06-01.md"
    report.write_text(SAMPLE_MD, encoding="utf-8")
    mock_resp = MagicMock()
    mock_resp.status_code = 422
    with patch("email_sender.requests.post", return_value=mock_resp), \
         patch.dict("os.environ", _env(), clear=True):
        from email_sender import send_report
        result = send_report(str(report))
    assert result is False


def test_send_report_returns_false_on_network_error(tmp_path):
    import requests as real_requests
    report = tmp_path / "2026-06-01.md"
    report.write_text(SAMPLE_MD, encoding="utf-8")
    with patch("email_sender.requests.post", side_effect=real_requests.RequestException("boom")), \
         patch.dict("os.environ", _env(), clear=True):
        from email_sender import send_report
        result = send_report(str(report))
    assert result is False
