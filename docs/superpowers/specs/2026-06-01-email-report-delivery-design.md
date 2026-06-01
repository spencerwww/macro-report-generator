# Email Report Delivery — Design

**Date:** 2026-06-01
**Status:** Approved, pending implementation

## Goal

Deliver each newly generated daily macro report to the user's inbox as a
readable, fully-rendered HTML email — removing the need to open the GitHub
`reports/` directory to read it. Delivery happens automatically after the daily
GitHub Actions run commits the report.

## Decisions (locked)

1. **Transport:** Resend transactional email API (free tier: 3,000/mo, 100/day).
2. **Body:** Full report converted markdown → styled HTML, readable inline.
3. **Failure mode:** Non-fatal. A send failure never breaks report generation
   and leaves the CI job green; the report is always committed first.
4. **Placement:** A separate CI step that runs *after* the commit/push step,
   not inside `main.py`.

## Architecture

One new module, mirroring the existing file-per-purpose layout:

```
src/email_sender.py   — markdown→HTML conversion + Resend API call
```

Public functions:

- `render_html(markdown_text: str, report_date: str) -> str`
  Converts report markdown to a styled, email-safe HTML document.
- `send_report(report_path: str) -> bool`
  Reads the file, renders it, POSTs to Resend. Never raises; logs a warning to
  stderr and returns `False` on any error (matches the project's
  graceful-degradation contract). Returns `True` on a 200 from Resend.

The module is invoked **standalone from the CI workflow**, not from `main.py`.
`main.py` stays focused on generating + committing the report; email is a
downstream concern that runs only after the commit succeeds. The script computes
today's report path (`reports/YYYY-MM-DD.md`, same UTC date logic as the
pipeline) or accepts it as a CLI argument.

### Dependencies

- Add `markdown` (Python-Markdown) to `requirements.txt`, used with the
  `tables` and `extra` extensions — the report is table-heavy.
- Resend is called via its REST endpoint using `requests` (no SDK), keeping the
  dependency footprint small.

## Configuration & secrets

Read inside `email_sender.py` via explicit `os.environ.get()` guards (mirrors the
existing Tavily warn-and-skip pattern):

| Var | Source | Required | Purpose |
|---|---|---|---|
| `RESEND_API_KEY` | new GitHub Actions secret | yes — missing ⇒ warn + return `False`, no send | auth |
| `REPORT_RECIPIENT_EMAIL` | new GitHub Actions secret (user's address) | yes — missing ⇒ warn + return `False` | recipient |
| `RESEND_FROM` | workflow `env:`, default `onboarding@resend.dev` | no | sender; allows swapping to a verified domain later with no code change |

Starting sender is Resend's shared sandbox `onboarding@resend.dev`, which can
send to a verified recipient immediately with no domain/DNS setup.

## HTML rendering

`render_html` wraps the converted markdown in a minimal HTML document with an
inline `<style>` block: readable font stack, constrained max-width, and bordered
tables (the 8 report tables read worst as raw text). Styling stays deliberately
simple for cross-client consistency (Gmail / Apple Mail / Outlook). A clean
single-column document with styled tables renders reliably.

Subject line: `Macro Report — YYYY-MM-DD`.

## Error handling & flow

```
CI: generate report → commit/push → [NEW] send email
```

The send step runs **after** commit, so the report is always safely in the repo
first. The step uses `continue-on-error: true` (and/or the script exits 0 on
failure) so a Resend outage leaves the job green and the report intact.

Every failure path returns `False` and logs to stderr without raising:
- missing `RESEND_API_KEY` or `REPORT_RECIPIENT_EMAIL`
- report file not found
- non-200 response from Resend
- network/exception during the POST

Nothing about email delivery can break report generation.

## Testing

New `tests/test_email_sender.py`, fully mocked (no real HTTP), matching the
existing 39-test mocked style:

- `render_html` produces HTML containing the report's table content.
- `send_report` POSTs with correct auth header and recipient when env is set.
- Missing `RESEND_API_KEY` ⇒ returns `False`, makes no HTTP call.
- Non-200 Resend response ⇒ returns `False`, does not raise.

## Documentation

Add an **Email delivery** section to `CLAUDE.md` documenting the new secrets,
the `RESEND_FROM` override, and where the CI step lives — consistent with the
existing watchlist / asset-addition touchpoint sections.

## CI integration

`.github/workflows/daily_report.yml` gains a step after "Commit and push report":

```yaml
- name: Email report
  continue-on-error: true
  env:
    RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
    REPORT_RECIPIENT_EMAIL: ${{ secrets.REPORT_RECIPIENT_EMAIL }}
    RESEND_FROM: onboarding@resend.dev
  run: PYTHONPATH=src python src/email_sender.py
```

## External setup (one-time, by user)

1. Create a free Resend account at resend.com.
2. Create an API key; add it as GitHub secret `RESEND_API_KEY`.
3. Add `REPORT_RECIPIENT_EMAIL` secret with the destination address.
4. (Optional, later) Verify a domain to send from a custom address via
   `RESEND_FROM`.

## Out of scope (YAGNI)

- Multiple recipients / mailing lists.
- Summary-only or digest emails.
- Configurable templates/themes.
- Retry/queue logic — daily cadence + non-fatal design makes this unnecessary.
