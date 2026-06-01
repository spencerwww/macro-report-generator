import os
import sys
import markdown as md

_STYLE = """
  body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         color: #1a1a1a; max-width: 760px; margin: 0 auto; padding: 24px;
         line-height: 1.5; }
  h1 { font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 6px; }
  h2 { font-size: 18px; margin-top: 28px; color: #222; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
  th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
  th { background: #f2f2f2; }
  a { color: #1a5fb4; }
"""


def render_html(markdown_text: str, report_date: str) -> str:
    """Convert report markdown to a styled, email-safe HTML document."""
    body = md.markdown(markdown_text, extensions=["tables", "extra"])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        f"<title>Macro Report — {report_date}</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )
