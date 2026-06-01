# Macro Report Generator

Automated daily macro trading report. Every day at **12:00 UTC** a GitHub Actions job fetches live financial data, asks Claude to synthesise a sourced report, fact-checks that report with a second Claude pass, commits the result to `reports/`, and emails it.

Each run produces one markdown file: `reports/YYYY-MM-DD.md`.

## How it works

The pipeline (`src/main.py`) runs six steps:

```
1. Fetch prices      yfinance — equities, FX, crypto, commodities + a personal watchlist
2. Fetch macro       FRED — CPI, PPI, Fed funds, and other US macro series
3. Fetch news        Tavily — 12 macro search queries, deduped by URL
4. Assemble bundle    {date, timestamp, prices, macro, news}
5. Generate report   Claude Agent 1 fills the 9-section template from the bundle
6. Fact-check        Claude Agent 2 cross-checks the report against the same bundle
```

The final report is written to `reports/<date>.md`. The previous two reports are passed
into step 5 as context so the narrative carries day to day.

### Two-agent design

- **`report_generator.py`** — synthesises the report from the data bundle and the
  `templates/report_template.md` template.
- **`fact_checker.py`** — a second Claude pass that re-reads the report against the bundle
  and corrects unsupported claims.

Both use **prompt caching**: the system prompt is held identical across runs (no per-run
`{DATE}`/`{TIME}` baked in) so the cache fires. Per-run values are passed in the user message.

### Graceful degradation

All three fetchers return partial or empty data on failure rather than raising — the
pipeline always produces a report even if a data source is down. Missing values appear as
`null` in the bundle and Claude is instructed to handle them. The FRED and Tavily API keys
are both optional: without them, macro values come back `None` and news comes back empty.

## Data sources

| Source | Library | Coverage |
|--------|---------|----------|
| Prices | `yfinance` | Equity indices (S&P 500, NASDAQ, DOW, VIX, Nikkei, DAX, KOSPI, ASX 200), FX majors + crosses, crypto (BTC/ETH/XRP/SOL), commodities (Brent, WTI, gold, silver, copper, nat gas) |
| Macro | `fredapi` | FRED series — CPI YoY%, PPI MoM%, Fed funds, etc. |
| News | `tavily-python` | 12 macro search queries (rates, oil, equities, geopolitics, crypto, FX, inflation, earnings…) |

The report also tracks a **personal watchlist** (Section 3) — hand-picked instruments
(`DSY.PA`, `SIE.DE`, `SMH`, `WQTM`) rendered alongside the broad macro feed.

## Report structure

The template (`templates/report_template.md`) drives a 9-section report:

1. Global Macro Overview
2. Conflict / Geopolitical Status
3. Personal Watchlist
4. Foreign Exchange
5. Commodities
6. Global Equity Indices
7. Cryptocurrency
8. All-Asset Summary Dashboard
9. Week Ahead / Scenario Analysis

…plus an Executive Summary at the top.

## Running locally

```bash
pip install -r requirements.txt
PYTHONPATH=src python src/main.py
```

Configure these environment variables (a `.env` file is loaded automatically via
`python-dotenv`):

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | yes | Claude report generation + fact-check |
| `FRED_API_KEY` | optional | FRED macro data (macro values are `null` without it) |
| `TAVILY_API_KEY` | optional | News context (news is empty without it) |
| `RESEND_API_KEY` | optional | Email delivery via Resend |
| `REPORT_RECIPIENT_EMAIL` | optional | Email destination address |

## Running tests

```bash
python -m pytest tests/ -v
```

Tests span the price fetcher, news fetcher, report generator, fact checker, email sender,
and main assembler. Every test uses mocks — no real API calls are made.

## GitHub Actions

`.github/workflows/daily_report.yml` runs on cron `0 12 * * *` (12:00 UTC) and can also be
triggered manually from **Actions → Daily Macro Report → Run workflow**. After generating
the report it commits `reports/YYYY-MM-DD.md` back to the repo as `github-actions[bot]`,
then emails it.

Required repository secrets (**Settings → Secrets and variables → Actions**):
`ANTHROPIC_API_KEY`, `FRED_API_KEY`, `TAVILY_API_KEY`, `RESEND_API_KEY`,
`REPORT_RECIPIENT_EMAIL`.

### Email delivery

After committing, the `Email report` step runs `src/email_sender.py`, which renders the
markdown to styled HTML and sends it via the Resend API. It is **non-fatal** — a delivery
failure logs to stderr and never fails the job or affects the committed report. The sender
address is set by the workflow `RESEND_FROM` env var (default `onboarding@resend.dev`,
Resend's shared sandbox sender); verify a domain in Resend and change it to send from a
custom address.

## Project layout

```
src/main.py              — pipeline entry point (run_pipeline + assemble_bundle)
src/price_fetcher.py     — yfinance prices + FRED macro
src/news_fetcher.py      — Tavily news search
src/report_generator.py  — Claude Agent 1: synthesises the report
src/fact_checker.py      — Claude Agent 2: fact-checks the report
src/email_sender.py      — renders markdown → HTML and sends via Resend
templates/report_template.md — 9-section report template
reports/                 — output, one markdown file per day
tests/                   — pytest suite (all mocked)
```

See [CLAUDE.md](CLAUDE.md) for design-decision details and contributor notes
(adding tickers, watchlist instruments, FRED series, etc.).
