# Macro Report Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that fetches live financial data daily, generates a sourced macro report via Claude, fact-checks it with a second Claude agent, and commits the output to GitHub via a scheduled Actions workflow.

**Architecture:** A deterministic data-fetching layer (yfinance + FRED + Tavily) assembles a structured bundle where every value is tagged with a source URL. Two sequential Claude claude-sonnet-4-6 calls then synthesise the report and append a fact-check section. GitHub Actions runs the pipeline at 12:00 UTC daily and commits the output markdown file.

**Tech Stack:** Python 3.12, `yfinance`, `fredapi`, `tavily-python`, `anthropic`, `python-dotenv`, `pytest`, `pytest-mock`, GitHub Actions

---

## File Map

| File | Responsibility |
|------|---------------|
| `src/price_fetcher.py` | Fetch equity, FX, crypto, commodity prices via yfinance; fetch macro indicators via FRED |
| `src/news_fetcher.py` | Run targeted Tavily searches; return structured list with source URLs |
| `src/report_generator.py` | Call Claude Agent 1 to synthesise the full report from the data bundle |
| `src/fact_checker.py` | Call Claude Agent 2 to fact-check the report and append findings |
| `src/main.py` | Orchestrate the full pipeline; save output file |
| `templates/report_template.md` | System prompt template defining the report format and rules |
| `tests/conftest.py` | Add `src/` to `sys.path` for all test files |
| `tests/test_price_fetcher.py` | Unit tests for price and macro fetchers (mocked APIs) |
| `tests/test_news_fetcher.py` | Unit tests for news fetcher (mocked Tavily) |
| `tests/test_report_generator.py` | Unit tests for Claude report generation (mocked Anthropic) |
| `tests/test_fact_checker.py` | Unit tests for Claude fact-checker (mocked Anthropic) |
| `tests/test_main.py` | Unit tests for bundle assembler |
| `.github/workflows/daily_report.yml` | Cron job: 12:00 UTC, runs pipeline, commits report |
| `requirements.txt` | All dependencies pinned |
| `.env.example` | Template for required environment variables |
| `.gitignore` | Excludes `.env`, `__pycache__`, reports from tracking (except `.gitkeep`) |
| `reports/.gitkeep` | Ensures `reports/` directory exists in repo |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `reports/.gitkeep`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`
- Create: `src/__init__.py`

- [ ] **Step 1: Initialise git repo**

```bash
cd C:\Users\spenc\OneDrive\Desktop\Projects\macro-report-generator
git init
```

Expected: `Initialized empty Git repository in ...`

- [ ] **Step 2: Create `requirements.txt`**

```
anthropic>=0.40.0
yfinance>=0.2.36
pandas>=2.0.0
fredapi>=0.5.1
tavily-python>=0.3.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create `.env.example`**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
FRED_API_KEY=your_fred_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
.DS_Store
```

- [ ] **Step 5: Create directory structure and placeholder files**

```bash
mkdir -p reports tests src templates
touch reports/.gitkeep
touch src/__init__.py
touch tests/__init__.py
```

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
```

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .env.example .gitignore reports/.gitkeep src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding"
```

---

## Task 2: Price Fetcher (yfinance)

**Files:**
- Create: `src/price_fetcher.py` (yfinance section only)
- Create: `tests/test_price_fetcher.py` (yfinance tests only)

- [ ] **Step 1: Write failing tests for `fetch_prices`**

Create `tests/test_price_fetcher.py`:

```python
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from price_fetcher import fetch_prices


def _mock_ticker(close_values):
    mock = MagicMock()
    mock.history.return_value = pd.DataFrame(
        {"Close": close_values},
        index=pd.to_datetime([f"2026-04-{14 + i}" for i in range(len(close_values))]),
    )
    return mock


def test_fetch_prices_returns_four_categories():
    with patch("yfinance.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    assert set(result.keys()) == {"equities", "fx", "crypto", "commodities"}


def test_fetch_prices_sp500_present():
    with patch("yfinance.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    assert "SP500" in result["equities"]


def test_fetch_prices_value_has_required_fields():
    with patch("yfinance.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    sp500 = result["equities"]["SP500"]
    assert "value" in sp500
    assert "change_pct" in sp500
    assert "source" in sp500
    assert "symbol" in sp500
    assert "as_of" in sp500


def test_fetch_prices_change_pct_calculation():
    with patch("yfinance.Ticker", return_value=_mock_ticker([100.0, 105.0])):
        result = fetch_prices()
    sp500 = result["equities"]["SP500"]
    assert sp500["change_pct"] == pytest.approx(5.0, rel=1e-3)


def test_fetch_prices_handles_empty_ticker_gracefully():
    mock = MagicMock()
    mock.history.return_value = pd.DataFrame()
    with patch("yfinance.Ticker", return_value=mock):
        result = fetch_prices()
    assert result["equities"]["SP500"]["value"] is None


def test_fetch_prices_all_fx_pairs_present():
    with patch("yfinance.Ticker", return_value=_mock_ticker([1.14, 1.142])):
        result = fetch_prices()
    for pair in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "DXY"]:
        assert pair in result["fx"], f"{pair} missing from fx"


def test_fetch_prices_all_crypto_present():
    with patch("yfinance.Ticker", return_value=_mock_ticker([73000.0, 74300.0])):
        result = fetch_prices()
    for asset in ["BTC", "ETH", "XRP", "SOL"]:
        assert asset in result["crypto"], f"{asset} missing from crypto"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_price_fetcher.py -v
```

Expected: `ImportError: No module named 'price_fetcher'` or similar — confirms tests are wired correctly.

- [ ] **Step 3: Create `src/price_fetcher.py` with yfinance fetching**

```python
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

EQUITY_TICKERS = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "VIX": "^VIX",
    "NIKKEI": "^N225",
    "DAX": "^GDAXI",
    "KOSPI": "^KS11",
    "ASX200": "^AXJO",
}

FX_TICKERS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "NZDUSD": "NZDUSD=X",
    "DXY": "DX-Y.NYB",
}

CRYPTO_TICKERS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "XRP": "XRP-USD",
    "SOL": "SOL-USD",
}

COMMODITY_TICKERS = {
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "NAT_GAS": "NG=F",
}


def _fetch_ticker_data(ticker_map: dict) -> dict:
    result = {}
    for name, symbol in ticker_map.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if hist.empty or len(hist) < 1:
                result[name] = {
                    "value": None,
                    "change_pct": None,
                    "source": f"Yahoo Finance ({symbol})",
                    "symbol": symbol,
                    "as_of": None,
                }
                continue
            latest = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else latest
            change_pct = round(((latest - prev) / prev) * 100, 2) if prev else None
            result[name] = {
                "value": round(latest, 4),
                "change_pct": change_pct,
                "source": f"Yahoo Finance ({symbol})",
                "symbol": symbol,
                "as_of": hist.index[-1].strftime("%Y-%m-%d"),
            }
        except Exception:
            result[name] = {
                "value": None,
                "change_pct": None,
                "source": f"Yahoo Finance ({symbol})",
                "symbol": symbol,
                "as_of": None,
            }
    return result


def fetch_prices() -> dict:
    """Fetch all price data from yfinance. Returns dict with source tags on every value."""
    return {
        "equities": _fetch_ticker_data(EQUITY_TICKERS),
        "fx": _fetch_ticker_data(FX_TICKERS),
        "crypto": _fetch_ticker_data(CRYPTO_TICKERS),
        "commodities": _fetch_ticker_data(COMMODITY_TICKERS),
    }
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_price_fetcher.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/price_fetcher.py tests/test_price_fetcher.py
git commit -m "feat: price fetcher via yfinance"
```

---

## Task 3: FRED Macro Fetcher

**Files:**
- Modify: `src/price_fetcher.py` (add `fetch_macro`)
- Modify: `tests/test_price_fetcher.py` (add FRED tests)

- [ ] **Step 1: Add failing FRED tests to `tests/test_price_fetcher.py`**

Append to the existing test file:

```python
from price_fetcher import fetch_macro


def test_fetch_macro_returns_required_keys():
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [3.3], index=pd.to_datetime(["2026-03-01"])
    )
    with patch("fredapi.Fred", return_value=mock_fred):
        result = fetch_macro()
    for key in ["cpi_yoy", "ppi_mom", "fed_funds", "treasury_10y", "treasury_2y"]:
        assert key in result, f"{key} missing from macro bundle"


def test_fetch_macro_values_have_source_and_url():
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [3.3], index=pd.to_datetime(["2026-03-01"])
    )
    with patch("fredapi.Fred", return_value=mock_fred):
        result = fetch_macro()
    cpi = result["cpi_yoy"]
    assert "value" in cpi
    assert "source" in cpi
    assert "url" in cpi
    assert "as_of" in cpi
    assert "fred.stlouisfed.org" in cpi["url"]


def test_fetch_macro_handles_fred_error_gracefully():
    mock_fred = MagicMock()
    mock_fred.get_series.side_effect = Exception("FRED API error")
    with patch("fredapi.Fred", return_value=mock_fred):
        result = fetch_macro()
    assert result["cpi_yoy"]["value"] is None
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
pytest tests/test_price_fetcher.py::test_fetch_macro_returns_required_keys -v
```

Expected: `ImportError: cannot import name 'fetch_macro'`

- [ ] **Step 3: Add `fetch_macro` to `src/price_fetcher.py`**

Add this import at the top of `price_fetcher.py`:

```python
from fredapi import Fred
```

Then append this constant and function to `price_fetcher.py`:

```python
FRED_SERIES = {
    "cpi_yoy": {
        "series_id": "CPIAUCSL",
        "url": "https://fred.stlouisfed.org/series/CPIAUCSL",
        "description": "CPI All Urban Consumers (YoY%)",
    },
    "ppi_mom": {
        "series_id": "PPIACO",
        "url": "https://fred.stlouisfed.org/series/PPIACO",
        "description": "PPI All Commodities",
    },
    "fed_funds": {
        "series_id": "FEDFUNDS",
        "url": "https://fred.stlouisfed.org/series/FEDFUNDS",
        "description": "Federal Funds Effective Rate",
    },
    "treasury_10y": {
        "series_id": "DGS10",
        "url": "https://fred.stlouisfed.org/series/DGS10",
        "description": "10-Year Treasury Yield",
    },
    "treasury_2y": {
        "series_id": "DGS2",
        "url": "https://fred.stlouisfed.org/series/DGS2",
        "description": "2-Year Treasury Yield",
    },
}


def fetch_macro() -> dict:
    """Fetch macro indicators from FRED. Returns dict with source URL on every value."""
    fred = Fred(api_key=os.environ["FRED_API_KEY"])
    result = {}
    for key, meta in FRED_SERIES.items():
        try:
            series = fred.get_series(meta["series_id"]).dropna()
            result[key] = {
                "value": round(float(series.iloc[-1]), 4),
                "as_of": series.index[-1].strftime("%Y-%m-%d"),
                "source": meta["description"],
                "url": meta["url"],
            }
        except Exception:
            result[key] = {
                "value": None,
                "as_of": None,
                "source": meta["description"],
                "url": meta["url"],
            }
    return result
```

- [ ] **Step 4: Run all price fetcher tests**

```bash
pytest tests/test_price_fetcher.py -v
```

Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/price_fetcher.py tests/test_price_fetcher.py
git commit -m "feat: FRED macro fetcher"
```

---

## Task 4: News Fetcher (Tavily)

**Files:**
- Create: `src/news_fetcher.py`
- Create: `tests/test_news_fetcher.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_news_fetcher.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from news_fetcher import fetch_news, DEFAULT_QUERIES


def _mock_tavily_client(results=None):
    mock = MagicMock()
    mock.search.return_value = {
        "results": results or [
            {
                "title": "Test Article",
                "content": "Test content about markets.",
                "url": "https://reuters.com/test",
                "published_date": "2026-04-16",
            }
        ]
    }
    return mock


def test_fetch_news_returns_list():
    with patch("tavily.TavilyClient", return_value=_mock_tavily_client()):
        result = fetch_news(["test query"])
    assert isinstance(result, list)
    assert len(result) > 0


def test_fetch_news_result_has_required_fields():
    with patch("tavily.TavilyClient", return_value=_mock_tavily_client()):
        result = fetch_news(["test query"])
    item = result[0]
    assert "query" in item
    assert "title" in item
    assert "content" in item
    assert "url" in item
    assert "published_date" in item


def test_fetch_news_query_echoed_in_result():
    with patch("tavily.TavilyClient", return_value=_mock_tavily_client()):
        result = fetch_news(["oil price today"])
    assert result[0]["query"] == "oil price today"


def test_fetch_news_handles_tavily_error_gracefully():
    mock = MagicMock()
    mock.search.side_effect = Exception("Tavily API error")
    with patch("tavily.TavilyClient", return_value=mock):
        result = fetch_news(["test query"])
    assert result == []


def test_fetch_news_empty_results_handled():
    with patch("tavily.TavilyClient", return_value=_mock_tavily_client(results=[])):
        result = fetch_news(["test query"])
    assert result == []


def test_default_queries_covers_key_topics():
    topics = " ".join(DEFAULT_QUERIES).lower()
    assert "federal reserve" in topics or "fed" in topics
    assert "oil" in topics or "brent" in topics
    assert "bitcoin" in topics or "crypto" in topics
    assert "inflation" in topics or "cpi" in topics
    assert "gold" in topics


def test_fetch_news_uses_default_queries_when_none_given():
    mock = _mock_tavily_client()
    with patch("tavily.TavilyClient", return_value=mock):
        fetch_news()
    assert mock.search.call_count == len(DEFAULT_QUERIES)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_news_fetcher.py -v
```

Expected: `ImportError: No module named 'news_fetcher'`

- [ ] **Step 3: Create `src/news_fetcher.py`**

```python
import os
from tavily import TavilyClient

DEFAULT_QUERIES = [
    "US Federal Reserve monetary policy interest rates latest",
    "Brent crude oil WTI price outlook today",
    "S&P 500 stock market outlook today",
    "geopolitical risk conflict global markets latest",
    "Bitcoin Ethereum cryptocurrency price today",
    "EUR USD GBP USD forex market today",
    "gold price inflation outlook today",
    "corporate earnings results today",
    "IMF World Bank global growth outlook",
    "central bank rate decisions hikes cuts",
    "US CPI PPI inflation data latest",
    "natural gas TTF Henry Hub price today",
]


def fetch_news(queries: list[str] = None) -> list[dict]:
    """
    Run Tavily searches for each query. Returns list of result dicts,
    each with query, title, content, url, and published_date fields.
    """
    if queries is None:
        queries = DEFAULT_QUERIES

    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = []

    for query in queries:
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_published_date=True,
            )
            for item in response.get("results", []):
                results.append({
                    "query": query,
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                    "published_date": item.get("published_date", ""),
                })
        except Exception:
            continue

    return results
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_news_fetcher.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/news_fetcher.py tests/test_news_fetcher.py
git commit -m "feat: news fetcher via Tavily"
```

---

## Task 5: Data Bundle Assembler

**Files:**
- Create: `src/main.py` (assembler only — pipeline added in Task 8)
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_main.py`:

```python
import pytest
from main import assemble_bundle, run_pipeline


def test_assemble_bundle_returns_required_keys():
    prices = {"equities": {}, "fx": {}, "crypto": {}, "commodities": {}}
    macro = {"cpi_yoy": {"value": 3.3}}
    news = [{"query": "test", "title": "Test", "content": "...", "url": "https://example.com"}]
    result = assemble_bundle(prices, macro, news)
    assert "date" in result
    assert "timestamp" in result
    assert "prices" in result
    assert "macro" in result
    assert "news" in result


def test_assemble_bundle_date_is_iso_format():
    result = assemble_bundle({}, {}, [])
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["date"])


def test_assemble_bundle_passthrough_unchanged():
    prices = {"equities": {"SP500": {"value": 6967.38}}}
    macro = {"cpi_yoy": {"value": 3.3}}
    news = [{"url": "https://reuters.com"}]
    result = assemble_bundle(prices, macro, news)
    assert result["prices"]["equities"]["SP500"]["value"] == 6967.38
    assert result["macro"]["cpi_yoy"]["value"] == 3.3
    assert result["news"][0]["url"] == "https://reuters.com"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_main.py -v
```

Expected: `ImportError: No module named 'main'`

- [ ] **Step 3: Create `src/main.py` with assembler**

```python
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def assemble_bundle(prices: dict, macro: dict, news: list[dict]) -> dict:
    """Combine fetched data into a single structured bundle with date and timestamp."""
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "macro": macro,
        "news": news,
    }
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_main.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: data bundle assembler"
```

---

## Task 6: Report Template

**Files:**
- Create: `templates/report_template.md`

- [ ] **Step 1: Create `templates/report_template.md`**

This file is the system prompt template passed to Claude Agent 1.

```markdown
# MACRO REPORT — {DATE}
**Delivered:** {TIME} UTC | **Generated by:** Claude claude-sonnet-4-6

---

## EXECUTIVE SUMMARY
Write 3-4 sentences capturing the dominant macro narrative for today. Identify the single most important variable for today's trading session. Include at least one inline source citation [Source: URL].

---

## 1. GLOBAL MACRO OVERVIEW
Write 3-5 paragraphs covering the macro backdrop: equity market status, key economic data released, central bank posture, and dominant risk narrative. Every specific data point (index levels, yields, inflation prints) must have an inline [Source: URL] citation.

---

## 2. CONFLICT / GEOPOLITICAL STATUS
**CONDITIONAL SECTION — only include if the news bundle contains material active geopolitical conflict or crisis.**
If included, use bullet points. Each bullet must be sourced:
- [Fact about conflict status]. [Source: URL]

If no material geopolitical conflict is present, omit this section entirely.

---

## 3. FOREIGN EXCHANGE
### Major Pairs

For each pair, use this exact block structure:

**{PAIR} — ~{LEVEL}** | Bias: {BIAS}
- {1-2 sentences of context}. [Source: URL]
- Key levels: {SUPPORT} support | {RESISTANCE} resistance
- Catalyst: {SPECIFIC UPCOMING CATALYST}

Cover all pairs in the dashboard: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, EUR/JPY, GBP/JPY, EUR/GBP

---

## 4. COMMODITIES
### Energy
For each commodity, use the same block structure as FX.
Cover: Brent Crude, WTI Crude, TTF Natural Gas, Henry Hub Natural Gas

### Precious Metals
Cover: Gold (XAU/USD), Silver (XAG/USD)

### Base Metals
Cover: Copper, Iron Ore (if data available)

---

## 5. GLOBAL EQUITY INDICES
### US Equities
Cover: S&P 500, Nasdaq 100, Dow Jones. Include earnings context if relevant.

### Asia
Cover: Nikkei 225, KOSPI, ASX 200

### Europe
Cover: DAX. Include ECB/BoE context.

---

## 6. CRYPTOCURRENCY
Cover each asset with the same block structure:
**{ASSET} — ~{LEVEL}** | Bias: {BIAS}
Cover: BTC, ETH, XRP, SOL

---

## 7. ALL-ASSET SUMMARY DASHBOARD

**This is the most important section. Populate every cell. Do not leave blanks.**

### FX
| PAIR | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
|------|-------|------|------------|--------------|-----------------|
| EUR/USD | | | | | |
| GBP/USD | | | | | |
| USD/JPY | | | | | |
| AUD/USD | | | | | |
| USD/CAD | | | | | |
| USD/CHF | | | | | |
| NZD/USD | | | | | |
| EUR/JPY | | | | | |
| GBP/JPY | | | | | |
| EUR/GBP | | | | | |

### Commodities
| ASSET | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
|-------|-------|------|------------|--------------|-----------------|
| Brent Crude | | | | | |
| WTI Crude | | | | | |
| TTF Nat Gas | | | | | |
| Henry Hub | | | | | |
| Gold | | | | | |
| Silver | | | | | |
| Copper | | | | | |

### Equities
| INDEX | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
|-------|-------|------|------------|--------------|-----------------|
| S&P 500 | | | | | |
| Nasdaq 100 | | | | | |
| Dow Jones | | | | | |
| ASX 200 | | | | | |
| Nikkei 225 | | | | | |
| KOSPI | | | | | |
| DAX | | | | | |

### Crypto
| ASSET | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
|-------|-------|------|------------|--------------|-----------------|
| BTC | | | | | |
| ETH | | | | | |
| XRP | | | | | |
| SOL | | | | | |

---

## 8. WEEK AHEAD / SCENARIO ANALYSIS

| SCENARIO | PROBABILITY | TRIGGER | BRENT | S&P 500 | BTC |
|----------|-------------|---------|-------|---------|-----|
| Bull | | | | | |
| Base | | | | | |
| Bear | | | | | |

List 3-5 key upcoming catalysts for the week with dates.

---

## INSTRUCTIONS FOR CLAUDE (REMOVE THIS SECTION FROM OUTPUT)
- Use exact price values from the data bundle. Never estimate or round differently from the source data.
- Every data point in sections 1-6 must have [Source: URL] from the bundle.
- BIAS options: Bullish / Neutral-Bull / Neutral / Neutral-Bear / Bearish
- RISK: 1 = very low volatility expected, 5 = binary/high-impact event imminent
- TRADE RANK: 1 = avoid, 5 = highest conviction setup
- Probabilities in scenario table must sum to 100%
- Do not include this INSTRUCTIONS section in the output
```

- [ ] **Step 2: Commit**

```bash
git add templates/report_template.md
git commit -m "feat: report template for Claude agent"
```

---

## Task 7: Report Generator (Claude Agent 1)

**Files:**
- Create: `src/report_generator.py`
- Create: `tests/test_report_generator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_report_generator.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from report_generator import generate_report

SAMPLE_BUNDLE = {
    "date": "2026-04-16",
    "timestamp": "2026-04-16T12:00:00Z",
    "prices": {
        "equities": {"SP500": {"value": 6967.38, "change_pct": 1.18, "source": "Yahoo Finance (^GSPC)"}},
        "fx": {},
        "crypto": {},
        "commodities": {},
    },
    "macro": {"cpi_yoy": {"value": 3.3, "url": "https://fred.stlouisfed.org/series/CPIAUCSL"}},
    "news": [{"query": "oil", "title": "Oil falls", "content": "Brent down 4%", "url": "https://reuters.com/1"}],
}

SAMPLE_TEMPLATE = "# MACRO REPORT — {DATE}\n\n## 7. ALL-ASSET SUMMARY DASHBOARD\n"


def test_generate_report_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT\n\nTest content")]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_uses_claude_sonnet():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"


def test_generate_report_uses_prompt_caching():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert any(
        isinstance(s, dict) and s.get("cache_control") == {"type": "ephemeral"}
        for s in system
    )


def test_generate_report_includes_bundle_date_in_message():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="# MACRO REPORT")]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        generate_report(SAMPLE_BUNDLE, SAMPLE_TEMPLATE)
    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "2026-04-16" in user_content
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_report_generator.py -v
```

Expected: `ImportError: No module named 'report_generator'`

- [ ] **Step 3: Create `src/report_generator.py`**

```python
import os
import json
import anthropic


def generate_report(data_bundle: dict, template: str) -> str:
    """
    Call Claude claude-sonnet-4-6 to synthesise the macro report from the data bundle.
    Uses prompt caching on the system prompt to reduce API costs on daily runs.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system_prompt = f"""You are a professional macro analyst generating a daily trading-oriented macro report.

Follow this template structure exactly:
{template}

Critical rules:
- Use ONLY the price values from the data bundle. Do not invent, estimate, or change values.
- Every specific data point must include an inline [Source: URL] citation from the data bundle.
- Populate every cell in the ALL-ASSET SUMMARY DASHBOARD tables — no blanks.
- BIAS options: Bullish / Neutral-Bull / Neutral / Neutral-Bear / Bearish
- RISK (1-5): 1 = low volatility, 5 = binary high-impact event imminent
- TRADE RANK (1-5): 1 = avoid, 5 = highest conviction setup
- Scenario probabilities must sum to 100%
- Omit the CONFLICT/GEOPOLITICAL STATUS section if no material geopolitical event is in the news bundle
- Remove the INSTRUCTIONS FOR CLAUDE section from the output
"""

    user_content = f"""Generate today's macro report using this data bundle:

{json.dumps(data_bundle, indent=2, default=str)}

Today's date: {data_bundle['date']}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_report_generator.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/report_generator.py tests/test_report_generator.py
git commit -m "feat: report generator Claude agent with prompt caching"
```

---

## Task 8: Fact-Checker (Claude Agent 2)

**Files:**
- Create: `src/fact_checker.py`
- Create: `tests/test_fact_checker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_fact_checker.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fact_checker import fact_check

SAMPLE_REPORT = """# MACRO REPORT — 2026-04-16

## EXECUTIVE SUMMARY
S&P 500 at 6,967.38, up 1.18%. Brent crude at $94.79. [Source: https://yahoo.com]
"""

SAMPLE_BUNDLE = {
    "date": "2026-04-16",
    "prices": {
        "equities": {"SP500": {"value": 6967.38, "change_pct": 1.18}},
        "commodities": {"BRENT": {"value": 94.79}},
    },
    "macro": {},
    "news": [],
}

FACT_CHECK_RESPONSE = """## FACT-CHECK & INSIGHTS

### Verified
- S&P 500 at 6,967.38 (+1.18%): confirmed via Yahoo Finance (^GSPC)

### Disputed
- None identified.

### Additional Insights
- VIX at recent lows suggests complacency risk ahead of key catalysts.
"""


def test_fact_check_returns_string():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert isinstance(result, str)


def test_fact_check_appends_to_original_report():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert SAMPLE_REPORT.strip() in result
    assert "## FACT-CHECK & INSIGHTS" in result


def test_fact_check_contains_three_subsections():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    assert "### Verified" in result
    assert "### Disputed" in result
    assert "### Additional Insights" in result


def test_fact_check_uses_prompt_caching():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=FACT_CHECK_RESPONSE)]
    )
    with patch("anthropic.Anthropic", return_value=mock_client):
        fact_check(SAMPLE_REPORT, SAMPLE_BUNDLE)
    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert any(
        isinstance(s, dict) and s.get("cache_control") == {"type": "ephemeral"}
        for s in system
    )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_fact_checker.py -v
```

Expected: `ImportError: No module named 'fact_checker'`

- [ ] **Step 3: Create `src/fact_checker.py`**

```python
import os
import json
import anthropic


def fact_check(report: str, data_bundle: dict) -> str:
    """
    Call Claude claude-sonnet-4-6 to fact-check the report against the raw data bundle.
    Returns the original report with a ## FACT-CHECK & INSIGHTS section appended.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system_prompt = """You are a rigorous fact-checker reviewing a macro trading report.

Your output must be a ## FACT-CHECK & INSIGHTS section with exactly these three sub-sections:

### Verified
List each claim from the report you confirmed against the data bundle.
Format each line as: - [CLAIM]: confirmed via [source from bundle]

### Disputed
List claims you could not verify or found conflicting evidence for.
Format each line as: - [CLAIM]: [specific reason / conflicting data point]
If nothing is disputed, write: - None identified.

### Additional Insights
Provide 3-5 insights relevant to the trading signals that the report did not include.
These must be grounded in the data bundle. Focus on what is most actionable for a trader.

Rules:
- Only cite URLs that appear in the data bundle — do not invent sources
- Be specific and concise — traders read this before market open
- Do not repeat information already in the report in the Verified section; just confirm it
"""

    user_content = f"""Fact-check this report against the raw data bundle.

RAW DATA BUNDLE:
{json.dumps(data_bundle, indent=2, default=str)}

REPORT TO FACT-CHECK:
{report}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    fact_check_section = response.content[0].text
    return f"{report}\n\n---\n\n{fact_check_section}"
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
pytest tests/test_fact_checker.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/fact_checker.py tests/test_fact_checker.py
git commit -m "feat: fact-checker Claude agent with prompt caching"
```

---

## Task 9: Main Orchestrator

**Files:**
- Modify: `src/main.py` (add `run_pipeline` and `__main__` block)
- Modify: `tests/test_main.py` (add pipeline test)

- [ ] **Step 1: Add failing pipeline test to `tests/test_main.py`**

Append to the existing `tests/test_main.py`:

```python
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os


def test_run_pipeline_saves_file(tmp_path, monkeypatch):
    # Change working directory so Path("templates/...") and Path("reports/...") resolve inside tmp_path
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "report_template.md").write_text("# Template")

    with patch("main.fetch_prices", return_value={"equities": {}, "fx": {}, "crypto": {}, "commodities": {}}), \
         patch("main.fetch_macro", return_value={}), \
         patch("main.fetch_news", return_value=[]), \
         patch("main.generate_report", return_value="# MACRO REPORT\n\nContent"), \
         patch("main.fact_check", return_value="# MACRO REPORT\n\nContent\n\n---\n\n## FACT-CHECK"):

        output_path = run_pipeline()

    assert Path(output_path).exists()
    content = Path(output_path).read_text()
    assert "MACRO REPORT" in content
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_main.py::test_run_pipeline_saves_file -v
```

Expected: `ImportError` or attribute error — `run_pipeline` not yet defined.

- [ ] **Step 3: Complete `src/main.py` with full pipeline**

Replace the contents of `src/main.py` with:

```python
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from price_fetcher import fetch_prices, fetch_macro
from news_fetcher import fetch_news, DEFAULT_QUERIES
from report_generator import generate_report
from fact_checker import fact_check


def assemble_bundle(prices: dict, macro: dict, news: list[dict]) -> dict:
    """Combine fetched data into a single structured bundle with date and timestamp."""
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "macro": macro,
        "news": news,
    }


def run_pipeline() -> str:
    """Run the full report generation pipeline. Returns path to output file."""
    print("[1/6] Fetching price data...")
    prices = fetch_prices()

    print("[2/6] Fetching macro indicators...")
    macro = fetch_macro()

    print("[3/6] Fetching news...")
    news = fetch_news(DEFAULT_QUERIES)

    print("[4/6] Assembling data bundle...")
    bundle = assemble_bundle(prices, macro, news)

    print("[5/6] Generating report...")
    template = Path("templates/report_template.md").read_text(encoding="utf-8")
    report = generate_report(bundle, template)

    print("[6/6] Running fact-check...")
    final_report = fact_check(report, bundle)

    output_path = Path(f"reports/{bundle['date']}.md")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(final_report, encoding="utf-8")

    print(f"Report saved to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    run_pipeline()
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS. Note: `test_run_pipeline_saves_file` may need the import order adjusted — if it fails with an import error, ensure `conftest.py` is adding `src/` to `sys.path` before the test runs.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: main pipeline orchestrator"
```

---

## Task 10: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily_report.yml`

- [ ] **Step 1: Create `.github/workflows/daily_report.yml`**

```yaml
name: Daily Macro Report

on:
  schedule:
    - cron: '0 12 * * *'   # 12:00 UTC daily
  workflow_dispatch:          # Allow manual trigger for testing

jobs:
  generate-report:
    runs-on: ubuntu-latest
    permissions:
      contents: write         # Required to commit the report file

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate report
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
        run: PYTHONPATH=src python src/main.py

      - name: Commit and push report
        run: |
          git config --local user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add reports/
          git diff --staged --quiet || (git commit -m "report: $(date -u +%Y-%m-%d)" && git push)
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily_report.yml
git commit -m "feat: GitHub Actions daily report workflow"
```

- [ ] **Step 3: Create GitHub repository and push**

```bash
git remote add origin https://github.com/YOUR_USERNAME/macro-report-generator.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

- [ ] **Step 4: Add secrets to GitHub repository**

In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `FRED_API_KEY` — from fred.stlouisfed.org/docs/api/api_key.html
- `TAVILY_API_KEY` — from tavily.com

- [ ] **Step 5: Run manual workflow trigger to verify end-to-end**

In your GitHub repo, go to **Actions → Daily Macro Report → Run workflow**.

Expected: Workflow completes successfully. A new file appears in `reports/YYYY-MM-DD.md`.

- [ ] **Step 6: Verify report file structure**

Open the committed report file and confirm:
- All 7 dashboard tables are populated (no blank cells)
- Every data point has a `[Source: URL]` citation
- The `## FACT-CHECK & INSIGHTS` section is appended with all three sub-sections

---

## API Keys to Acquire Before Starting

| Service | URL | Notes |
|---------|-----|-------|
| Anthropic | console.anthropic.com | Paid, ~$5-8/month at daily usage |
| FRED | fred.stlouisfed.org/docs/api/api_key.html | Free, instant |
| Tavily | tavily.com | Free tier: 1,000 searches/month |
