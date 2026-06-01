# Macro Report Generator

Automated daily macro trading report. Runs at 12:00 UTC via GitHub Actions, fetches live financial data, generates a sourced report via Claude claude-sonnet-4-6, fact-checks it with a second Claude pass, and commits the output as a markdown file to `reports/`.

## Architecture

```
src/main.py          — pipeline entry point (run_pipeline + assemble_bundle)
src/price_fetcher.py — yfinance (equities/FX/crypto/commodities) + FRED (macro)
src/news_fetcher.py  — Tavily search, 12 macro queries
src/report_generator.py — Claude Agent 1: synthesises report from data bundle
src/fact_checker.py  — Claude Agent 2: cross-checks report against data bundle
templates/report_template.md — 8-section report template passed to Claude
reports/             — output directory, one markdown file per day (YYYY-MM-DD.md)
```

## Running locally

```bash
pip install -r requirements.txt
PYTHONPATH=src python src/main.py
```

Requires env vars: `ANTHROPIC_API_KEY`, `FRED_API_KEY`, `TAVILY_API_KEY` (TAVILY optional — reports still generate without news context).

## Running tests

```bash
python -m pytest tests/ -v
```

39 tests across price fetcher, news fetcher, report generator, fact checker, and main assembler. All use mocks — no real API calls in tests.

## Key design decisions

**Prompt caching:** `report_generator.py` and `fact_checker.py` pass the system prompt with `cache_control: {"type": "ephemeral"}`. For caching to fire, the system prompt must be identical across runs — so `{DATE}` and `{TIME}` are NOT substituted into the system prompt. They are passed via the user message instead, where Claude is instructed to replace them. Do not add per-run values to the system prompt.

**Data bundle contract:** `assemble_bundle()` returns `{date, timestamp, prices, macro, news}`. The `prices` and `macro` dicts are deep-copied on ingestion so downstream mutation doesn't corrupt the bundle. Do not change these keys — `report_generator` and `fact_checker` both depend on the shape.

**FRED series transforms:** CPI and PPI are raw index levels from FRED, not percentages. `price_fetcher.py` calculates YoY% and MoM% manually. The `FRED_SERIES` dict has a `"transform"` field (`"yoy_pct"` or `"mom_pct"`) to signal this. If adding new FRED series, check whether it's a raw index or already a rate.

**Graceful degradation:** All three fetchers (`fetch_prices`, `fetch_macro`, `fetch_news`) return partial/empty data on failure rather than raising. The pipeline always produces a report even if some data sources are down. Missing values appear as `null` in the bundle; Claude handles them.

**FRED API key:** Optional at fetch time — `Fred()` constructor is wrapped in a try/except. If `FRED_API_KEY` is missing or invalid, all macro values return `None`.

**Tavily API key:** Guarded with an explicit `os.environ.get()` check. If missing, `fetch_news` returns `[]` with a stderr warning and the pipeline continues.

## GitHub Actions

`.github/workflows/daily_report.yml` — cron `0 12 * * *` (12:00 UTC). After generating the report, it commits `reports/YYYY-MM-DD.md` back to the repo via `github-actions[bot]`.

Secrets required in **Settings → Secrets and variables → Actions → Repository secrets**:
- `ANTHROPIC_API_KEY`
- `FRED_API_KEY`
- `TAVILY_API_KEY`

Manual trigger available via **Actions → Daily Macro Report → Run workflow**.

### Email delivery

After the report is committed, the `Email report` step runs `src/email_sender.py`, which renders the markdown to styled HTML and sends it via the Resend API. It is **non-fatal** (`continue-on-error: true`, and the script always exits 0) — a delivery failure never fails the job or affects the committed report.

Additional secrets:
- `RESEND_API_KEY` — Resend API key.
- `REPORT_RECIPIENT_EMAIL` — destination address.

The sender is set via the workflow `env:` `RESEND_FROM` (default `onboarding@resend.dev`, Resend's shared sandbox sender). To send from a custom address, verify a domain in Resend and change `RESEND_FROM` in the workflow — no code change needed. `send_report` follows the same warn-and-skip degradation as the fetchers: missing keys, a missing report file, or a non-2xx response log to stderr and return `False`.

## Shell commands

Run each command in its own shell call — do not chain with `&&`.

## Adding assets

To add a new ticker to the price feed, add it to the relevant dict in `src/price_fetcher.py` (`EQUITY_TICKERS`, `FX_TICKERS`, `CRYPTO_TICKERS`, or `COMMODITY_TICKERS`) and add the corresponding row to the relevant table in `templates/report_template.md`. Then add a test in `tests/test_price_fetcher.py` asserting the asset is present.

### Personal watchlist (add/remove a ticker)

The watchlist is the personal list of instruments rendered as Section 3 of the report. To add or remove one, edit these four places — all keyed by the short name (e.g. `DSY`) and its Yahoo Finance symbol (e.g. `DSY.PA`):

1. **`src/price_fetcher.py`** — the `WATCHLIST_TICKERS` dict (`"NAME": "YAHOO_SYMBOL"`). This is the only data-layer change; it flows into the bundle as `prices["watchlist"]` automatically.
2. **`templates/report_template.md`** — the `Cover all watchlist instruments:` line in **Section 3. PERSONAL WATCHLIST** (the prose list Claude renders one block per).
3. **`templates/report_template.md`** — the `### Watchlist` table in **Section 8. ALL-ASSET SUMMARY DASHBOARD** (one row per instrument).
4. **`tests/test_price_fetcher.py`** — `test_fetch_prices_all_watchlist_present` and `test_fetch_prices_watchlist_symbols_map_correctly`.

US-listed symbols use the bare ticker (e.g. `SMH`, `WQTM`); non-US listings need the Yahoo exchange suffix (`.PA` Paris, `.DE` XETRA, `.L` London, `.MI` Milan). Verify a new symbol resolves on Yahoo before committing — an unresolvable symbol degrades to `null` rather than erroring, so it fails silently. Run `python -m pytest tests/test_price_fetcher.py -v` after editing.
