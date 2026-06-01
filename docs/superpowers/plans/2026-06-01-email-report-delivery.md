# Email Report Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Email each newly generated daily macro report to the user as styled HTML, via Resend, as a non-fatal CI step after the report is committed.

**Architecture:** A new standalone module `src/email_sender.py` converts the report markdown to a styled HTML document (`render_html`) and POSTs it to the Resend REST API (`send_report`). It runs as its own GitHub Actions step after the commit/push step, never raising and never affecting report generation. All failure paths log to stderr and return `False`.

**Tech Stack:** Python 3.12, `markdown` (Python-Markdown, `tables`+`extra` extensions), `requests` for the Resend REST call, `pytest` + `unittest.mock` for fully-mocked tests.

---

### Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add `markdown` and `requests` to requirements.txt**

Append these two lines to `requirements.txt` (after `pytest-mock`):

```
markdown>=3.5,<4.0.0
requests>=2.31.0,<3.0.0
```

- [ ] **Step 2: Install to verify they resolve**

Run: `C:\Users\spenc\anaconda3\python.exe -m pip install -r requirements.txt`
Expected: installs/confirms `markdown` and `requests` with no resolver errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: add markdown and requests for email delivery"
```

---

### Task 2: `render_html` — convert report markdown to styled HTML

**Files:**
- Create: `src/email_sender.py`
- Test: `tests/test_email_sender.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_email_sender.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'email_sender'`.

(Tests run with `PYTHONPATH=src`; the project's other tests rely on the same. If import fails, run `set PYTHONPATH=src` first or invoke `python -m pytest` from the repo root where `conftest`/pytest picks up `src`.)

- [ ] **Step 3: Write minimal implementation**

Create `src/email_sender.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py -v`
Expected: PASS — all 4 `render_html` tests green.

- [ ] **Step 5: Commit**

```bash
git add src/email_sender.py tests/test_email_sender.py
git commit -m "feat: render report markdown to styled HTML for email"
```

---

### Task 3: `send_report` — success path

**Files:**
- Modify: `src/email_sender.py`
- Test: `tests/test_email_sender.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_email_sender.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py::test_send_report_posts_to_resend_and_returns_true -v`
Expected: FAIL — `ImportError: cannot import name 'send_report'`.

- [ ] **Step 3: Write minimal implementation**

Add to the top imports of `src/email_sender.py`:

```python
import os
import sys
import re
import requests
import markdown as md
```

Add these functions to `src/email_sender.py`:

```python
RESEND_ENDPOINT = "https://api.resend.com/emails"


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
    html = render_html(markdown_text, report_date)

    try:
        resp = requests.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": sender,
                "to": recipient,
                "subject": f"Macro Report — {report_date}",
                "html": html,
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py -v`
Expected: PASS — all tests including the new send-success test.

- [ ] **Step 5: Commit**

```bash
git add src/email_sender.py tests/test_email_sender.py
git commit -m "feat: send rendered report to Resend"
```

---

### Task 4: `send_report` — failure paths (graceful degradation)

**Files:**
- Test: `tests/test_email_sender.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_email_sender.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py -v`
Expected: PASS — all failure-path tests green (the implementation from Task 3 already handles these). If any fail, fix `send_report` to match the guard order in Task 3 before proceeding.

- [ ] **Step 3: Commit**

```bash
git add tests/test_email_sender.py
git commit -m "test: cover email_sender graceful-degradation paths"
```

---

### Task 5: CLI entry point — compute today's report path

**Files:**
- Modify: `src/email_sender.py`
- Test: `tests/test_email_sender.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_email_sender.py`:

```python
def test_default_report_path_uses_utc_today():
    from email_sender import default_report_path
    from datetime import datetime, timezone
    expected = f"reports/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    assert default_report_path() == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py::test_default_report_path_uses_utc_today -v`
Expected: FAIL — `ImportError: cannot import name 'default_report_path'`.

- [ ] **Step 3: Write minimal implementation**

Add `from datetime import datetime, timezone` to the imports of `src/email_sender.py`, then add:

```python
def default_report_path() -> str:
    """reports/YYYY-MM-DD.md for today's UTC date (matches the pipeline)."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"reports/{date}.md"


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else default_report_path()
    ok = send_report(path)
    # Non-fatal: always exit 0 so a delivery failure never fails the CI job.
    sys.exit(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/test_email_sender.py -v`
Expected: PASS — all email_sender tests green.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/ -v`
Expected: PASS — original 39 tests plus the new email_sender tests.

- [ ] **Step 6: Commit**

```bash
git add src/email_sender.py tests/test_email_sender.py
git commit -m "feat: add CLI entry point for email_sender"
```

---

### Task 6: Wire the email step into GitHub Actions

**Files:**
- Modify: `.github/workflows/daily_report.yml`

- [ ] **Step 1: Add the email step after the commit step**

In `.github/workflows/daily_report.yml`, after the `Commit and push report` step (the last step, ending at the `git push` line), append this new step at the same indentation level:

```yaml
      - name: Email report
        continue-on-error: true
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          REPORT_RECIPIENT_EMAIL: ${{ secrets.REPORT_RECIPIENT_EMAIL }}
          RESEND_FROM: onboarding@resend.dev
        run: PYTHONPATH=src python src/email_sender.py
```

- [ ] **Step 2: Validate YAML parses**

Run: `C:\Users\spenc\anaconda3\python.exe -c "import yaml; yaml.safe_load(open('.github/workflows/daily_report.yml')); print('ok')"`
Expected: prints `ok` (no YAML parse error).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily_report.yml
git commit -m "ci: email the report after committing it"
```

---

### Task 7: Document the feature in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add an Email delivery section**

In `CLAUDE.md`, under the `## GitHub Actions` section, after the existing secrets list (the three `ANTHROPIC_API_KEY` / `FRED_API_KEY` / `TAVILY_API_KEY` bullets), add:

```markdown
### Email delivery

After the report is committed, the `Email report` step runs
`src/email_sender.py`, which renders the markdown to styled HTML and sends it via
the Resend API. It is **non-fatal** (`continue-on-error: true`, and the script
always exits 0) — a delivery failure never fails the job or affects the
committed report.

Additional secrets:
- `RESEND_API_KEY` — Resend API key.
- `REPORT_RECIPIENT_EMAIL` — destination address.

The sender is set via the workflow `env:` `RESEND_FROM` (default
`onboarding@resend.dev`, Resend's shared sandbox sender). To send from a custom
address, verify a domain in Resend and change `RESEND_FROM` in the workflow — no
code change needed. `send_report` follows the same warn-and-skip degradation as
the fetchers: missing keys, a missing report file, or a non-2xx response log to
stderr and return `False`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document email delivery step in CLAUDE.md"
```

---

## Final verification

- [ ] Run the full test suite: `C:\Users\spenc\anaconda3\python.exe -m pytest tests/ -v` — all tests pass.
- [ ] Confirm `git status` is clean and all 7 task commits are present.
- [ ] Remind the user of the one-time external setup: create a Resend account, add `RESEND_API_KEY` and `REPORT_RECIPIENT_EMAIL` as GitHub Actions repository secrets, and (in Resend) verify their recipient address for the sandbox sender.
