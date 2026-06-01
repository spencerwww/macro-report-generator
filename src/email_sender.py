import os
import sys
import re
import html
import requests
import markdown as md
from datetime import datetime, timezone

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


RESEND_ENDPOINT = "https://api.resend.com/emails"


def render_html(markdown_text: str, report_date: str) -> str:
    """Convert report markdown to a styled, email-safe HTML document."""
    body = md.markdown(markdown_text, extensions=["tables", "extra"])
    safe_date = html.escape(report_date)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        f"<title>Macro Report — {safe_date}</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )


def _report_date_from_path(report_path: str) -> str:
    """Extract YYYY-MM-DD from a reports/YYYY-MM-DD.md path, else empty string."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(report_path))
    return m.group(1) if m else ""


def send_report(report_path: str) -> bool:
    """Read the report, render HTML, POST to Resend. Never raises.

    Returns True only on a 2xx response. Logs a warning and returns False on any
    failure (missing env, missing file, non-2xx, network error).
    """
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("REPORT_RECIPIENT_EMAIL")
    sender = os.environ.get("RESEND_FROM", "onboarding@resend.dev")

    if not api_key:
        print("[email_sender] WARNING: RESEND_API_KEY not set — skipping email", file=sys.stderr)
        return False
    if not recipient:
        print("[email_sender] WARNING: REPORT_RECIPIENT_EMAIL not set — skipping email", file=sys.stderr)
        return False

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()
    except OSError as e:
        print(f"[email_sender] WARNING: could not read {report_path}: {e}", file=sys.stderr)
        return False

    report_date = _report_date_from_path(report_path)
    html_body = render_html(markdown_text, report_date)

    try:
        resp = requests.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": sender,
                "to": recipient,
                "subject": f"Macro Report — {report_date}",
                "html": html_body,
            },
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"[email_sender] WARNING: Resend request failed: {e}", file=sys.stderr)
        return False

    if resp.status_code // 100 != 2:
        print(f"[email_sender] WARNING: Resend returned {resp.status_code}", file=sys.stderr)
        return False

    print(f"[email_sender] Sent report {report_date} to {recipient}")
    return True


def default_report_path() -> str:
    """reports/YYYY-MM-DD.md for today's UTC date (matches the pipeline)."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"reports/{date}.md"


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else default_report_path()
    ok = send_report(path)
    # Non-fatal: always exit 0 so a delivery failure never fails the CI job.
    sys.exit(0)
