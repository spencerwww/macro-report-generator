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
    assert "<td>S&amp;P 500</td>" in html or "<td>S&P 500</td>" in html


def test_render_html_includes_heading_content():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "Executive Summary" in html
    assert "Markets were mixed today." in html


def test_render_html_includes_inline_style_block():
    html = render_html(SAMPLE_MD, "2026-06-01")
    assert "<style>" in html
    assert "table" in html  # table styling present
