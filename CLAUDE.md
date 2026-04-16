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

## Shell commands

Run each command in its own shell call — do not chain with `&&`.

## Adding assets

To add a new ticker to the price feed, add it to the relevant dict in `src/price_fetcher.py` (`EQUITY_TICKERS`, `FX_TICKERS`, `CRYPTO_TICKERS`, or `COMMODITY_TICKERS`) and add the corresponding row to the relevant table in `templates/report_template.md`. Then add a test in `tests/test_price_fetcher.py` asserting the asset is present.
