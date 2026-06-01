# Personal Watchlist Section — Design

**Date:** 2026-06-01
**Status:** Approved (pending spec review)

## Goal

Add a personal watchlist of hand-picked instruments to the daily macro report.
The watchlist covers the same per-instrument information as the existing ticker
sections (level, daily change, bias, context, catalyst) and appears as its own
report section immediately after the Conflict / Geopolitical Status section.

Initial watchlist:

| Key    | Yahoo symbol | Instrument                                    |
|--------|--------------|-----------------------------------------------|
| DSY    | `DSY.PA`     | Dassault Systèmes (Euronext Paris)            |
| SIE    | `SIE.DE`     | Siemens (XETRA)                               |
| SMH    | `SMH`        | VanEck Semiconductor ETF (US)                 |
| WQTM   | `WQTM`       | WisdomTree Quantum Computing ETF (US/Nasdaq line, USD) |

## Approach

Hardcoded ticker dict, mirroring the existing `EQUITY_TICKERS` / `FX_TICKERS`
pattern. The list is edited in code, the same way any other asset is added per
the CLAUDE.md "Adding assets" convention. No external config file — YAGNI for a
short, infrequently-changed list.

## Changes

### 1. `src/price_fetcher.py`

- Add a new ticker dict:

  ```python
  WATCHLIST_TICKERS = {
      "DSY": "DSY.PA",
      "SIE": "SIE.DE",
      "SMH": "SMH",
      "WQTM": "WQTM",
  }
  ```

- In `fetch_prices()`, add `"watchlist": _fetch_ticker_data(WATCHLIST_TICKERS)`
  to the returned dict. Each entry uses the existing
  `{value, change_pct, source, symbol, as_of}` shape produced by the shared
  `_fetch_ticker_data` helper. Graceful degradation (null on fetch failure) is
  already handled by that helper — no extra error handling needed.

### 2. Data bundle — no change

`assemble_bundle()` is untouched. The new `watchlist` key lives **inside** the
existing `prices` dict, so the top-level bundle contract
`{date, timestamp, prices, macro, news}` is preserved. `report_generator` and
`fact_checker` both consume the bundle generically and need no changes.

### 3. `templates/report_template.md`

- Insert a new section **`## 3. PERSONAL WATCHLIST`** immediately after
  `## 2. CONFLICT / GEOPOLITICAL STATUS`. It uses the same block structure as the
  FX / commodities / crypto sections:

  ```
  **{ASSET} — ~{LEVEL}** | Bias: {BIAS}
  - {1-2 sentences of context}. [Source: URL]
  - Catalyst: {SPECIFIC UPCOMING CATALYST}

  Cover: Dassault Systèmes (DSY.PA), Siemens (SIE.DE), SMH, WQTM
  ```

- Renumber the remaining sections: Foreign Exchange 3→4, Commodities 4→5,
  Global Equity Indices 5→6, Cryptocurrency 6→7, All-Asset Summary Dashboard
  7→8, Week Ahead / Scenario Analysis 8→9.

- Add a **Watchlist** table to the All-Asset Summary Dashboard (renumbered
  Section 8) with the same columns used by the other dashboard groups:

  ```
  ### Watchlist
  | ASSET | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
  |-------|-------|------|------------|--------------|-----------------|
  | DSY (Dassault Systèmes) | | | | | |
  | SIE (Siemens) | | | | | |
  | SMH | | | | | |
  | WQTM | | | | | |
  ```

- Update the INSTRUCTIONS section's placeholder-substitution line: the range
  "Sections 3-6" must widen to include the new watchlist section (e.g.
  "Sections 3-7") so `{ASSET}` / `{LEVEL}` / `{BIAS}` tokens in the watchlist are
  substituted.

### 4. `tests/test_price_fetcher.py`

- Add a test asserting that all four watchlist keys appear under
  `fetch_prices()["watchlist"]` and map to the expected Yahoo symbols, following
  the CLAUDE.md "Adding assets" convention (mocked — no live API calls).

### 5. `fact_checker.py` — no change

Reads the whole bundle generically; will cross-check watchlist values like any
other price.

## Verification

- `WQTM` (bare US symbol) must be confirmed to return data from Yahoo Finance
  during implementation. If it does not resolve, it degrades to `null` and Claude
  notes the data is unavailable — but the implementer should flag a non-resolving
  symbol to the user so a corrected symbol can be substituted.
- Run `python -m pytest tests/ -v` — all existing tests plus the new watchlist
  test pass.

## Out of scope

- No support/resistance levels (those were just removed from the template).
- No per-instrument fundamentals (P/E, market cap) beyond what the other ticker
  sections carry.
- No external/editable config — list is code-defined.
