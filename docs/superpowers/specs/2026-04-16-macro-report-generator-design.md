# Macro Report Generator — Design Spec
**Date:** 2026-04-16
**Status:** Approved

---

## Overview

An automated daily macro report generator that runs at 12:00 UTC via GitHub Actions. It fetches live financial data and news from free-tier APIs, synthesises a structured macro report using Claude claude-sonnet-4-6, then runs a second Claude agent to fact-check and append insights. Output is a markdown file committed to a `reports/` directory in the GitHub repository.

The report is used as input to an automated trading strategy. The all-asset summary dashboard is the most critical section.

---

## Architecture

### Data Flow

```
GitHub Actions (cron: 12:00 UTC daily)
        │
        ▼
┌─────────────────────────────────────┐
│         PIPELINE ORCHESTRATOR       │
│           (main.py)                 │
└──────────┬──────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌──────────┐
│  Price  │  │  News &  │
│ Fetcher │  │  Macro   │
│(yfinance│  │ Fetcher  │
│  FRED)  │  │ (Tavily) │
└────┬────┘  └────┬─────┘
     └─────┬──────┘
           ▼
┌─────────────────────┐
│   Data Bundle       │  ← structured dict, all values tagged with source + timestamp
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  REPORT GENERATOR   │  ← Claude claude-sonnet-4-6, given bundle + blueprint template
│  (Claude Agent 1)   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   FACT-CHECKER      │  ← Claude claude-sonnet-4-6, given report + raw bundle
│  (Claude Agent 2)   │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  OUTPUT: .md file   │  ← reports/YYYY-MM-DD.md, committed to repo
└─────────────────────┘
```

**Core principle:** Data fetching is deterministic and testable. Claude only performs synthesis and analysis. Every value in the data bundle carries a source URL and timestamp before Claude sees it.

---

## Repository Structure

```
macro-report-generator/
├── .github/
│   └── workflows/
│       └── daily_report.yml    ← cron trigger (12:00 UTC)
├── src/
│   ├── main.py                 ← pipeline orchestrator
│   ├── price_fetcher.py        ← yfinance + FRED API
│   ├── news_fetcher.py         ← Tavily web search
│   ├── report_generator.py     ← Claude Agent 1 (report writer)
│   └── fact_checker.py         ← Claude Agent 2 (fact-checker)
├── templates/
│   └── report_template.md      ← system prompt template for Agent 1
├── reports/
│   └── YYYY-MM-DD.md           ← daily output files
├── requirements.txt
└── .env.example                ← API key template (never committed)
```

---

## Data Sources

| Source | API Key Required | What It Covers |
|--------|-----------------|----------------|
| `yfinance` | No | Equity indices, FX pairs, crypto, commodities (Brent, WTI, Gold, Silver, Copper), VIX |
| `FRED API` | Yes (free) | CPI, PPI, Fed Funds rate, 10Y/2Y Treasury yields, DXY, import/export prices |
| `Tavily API` | Yes (free tier: 1,000 searches/month) | Geopolitical news, earnings, central bank statements, analyst commentary, TTF/Henry Hub gas prices |

### Coverage mapping

| Report Section | Primary Source |
|----------------|---------------|
| Price levels & % moves | yfinance |
| US macro indicators (CPI, PPI, yields) | FRED |
| Geopolitics, earnings, analyst views | Tavily |
| Central bank decisions | Tavily + FRED |
| TTF / Henry Hub gas | Tavily (news-sourced) |

### Known gap
TTF and Henry Hub natural gas prices are not reliably available via yfinance. These will be retrieved via Tavily search (e.g., from Trading Economics or Reuters). This is a known trade-off of free-tier constraints — values will be approximate and sourced from a news reference rather than a live feed.

---

## Agent Design

### Agent 1 — Report Generator (claude-sonnet-4-6)

**Input:**
- Full structured data bundle (all values tagged with source URL + timestamp)
- System prompt containing the report template
- Today's date

**Task:** Write the full report in the template format. Every factual claim must include an inline `[Source: URL]` citation drawn from the data bundle. The all-asset dashboard tables are populated directly from the price data; Claude fills in BIAS, RISK, and KEY CATALYST columns based on news context.

**Prompt caching** applied to system prompt to reduce API costs on repeated daily runs.

### Agent 2 — Fact-Checker (claude-sonnet-4-6)

**Input:**
- Completed report from Agent 1
- Raw data bundle (for cross-checking claims against primary data)

**Task:** Produce the appended `## FACT-CHECK & INSIGHTS` section with three sub-sections:
1. **Verified** — claims confirmed against the data bundle or secondary search
2. **Disputed** — claims that could not be verified or have conflicting information, with explanation
3. **Additional Insights** — relevant context Agent 1 missed that supports or opposes the trading signals

The fact-checker runs targeted Tavily searches only for claims it flags as uncertain — it does not re-search everything.

**Prompt caching** applied to system prompt.

---

## Output Format

```markdown
# MACRO REPORT — {DATE}
**Delivered:** {TIME} AEDT | **Generated by:** Claude claude-sonnet-4-6

---

## EXECUTIVE SUMMARY
3-4 sentence dominant narrative. Key variable for today's session.

---

## 1. GLOBAL MACRO OVERVIEW
Narrative paragraphs. Inline citations [Source: URL].

---

## 2. CONFLICT / GEOPOLITICAL STATUS
(Conditional section — only included when a material conflict or geopolitical event is active)
Bullet-point format. Each bullet sourced.

---

## 3. FOREIGN EXCHANGE
### Major Pairs
**EUR/USD — ~1.1420** | Bias: Neutral-Bull
- Key context. [Source: URL]

(one block per pair)

---

## 4. COMMODITIES
### Energy | Precious Metals | Base Metals
(one block per asset)

---

## 5. GLOBAL EQUITY INDICES
### US | Asia | Europe
(one block per index)

---

## 6. CRYPTOCURRENCY
(one block per asset)

---

## 7. ALL-ASSET SUMMARY DASHBOARD

### FX
| PAIR | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |
|------|-------|------|------------|--------------|-----------------|

### Commodities
| ASSET | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |

### Equities
| INDEX | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |

### Crypto
| ASSET | LEVEL | BIAS | RISK (1-5) | KEY CATALYST | TRADE RANK (1-5) |

---

## 8. WEEK AHEAD / SCENARIO ANALYSIS
Scenario table: Base case / Bull / Bear with probability and price targets.

---

## FACT-CHECK & INSIGHTS
### Verified
### Disputed
### Additional Insights
```

### Format decisions
- **Geopolitical section is conditional** — omitted on quiet days rather than padded with filler
- **Crypto included in dashboard tables** — present in body sections of the blueprint but missing from dashboard; added since it is part of the trading strategy
- **Consistent per-asset block structure** — each asset/pair follows the same format for machine parseability

---

## GitHub Actions Setup

### Workflow (`daily_report.yml`)
- **Schedule:** `cron: '0 12 * * *'` (fixed at 12:00 UTC daily)
- **Local time note:** 12:00 UTC = 10:00 PM AEST (Apr–Oct) and 11:00 PM AEDT (Oct–Apr). No DST handling required — UTC is the fixed reference.
- **Steps:** checkout → install deps → run `main.py` → commit output to `reports/YYYY-MM-DD.md`
- **Failure handling:** GitHub sends automatic email on workflow failure

### Secrets (stored in GitHub Actions secrets, never in code)
- `ANTHROPIC_API_KEY`
- `FRED_API_KEY`
- `TAVILY_API_KEY`

---

## Cost Estimate (per daily run)

| Service | Usage | Cost |
|---------|-------|------|
| yfinance | Unlimited | Free |
| FRED API | ~10-15 calls/run | Free |
| Tavily | ~15-25 searches/run (~500/month) | Free (under 1,000/month limit) |
| Claude API (Sonnet) | ~30-40k tokens/run | ~$0.15-0.25/day |

Monthly Claude API cost estimate: **~$5-8/month**

---

## API Keys to Acquire

1. **Anthropic API** — console.anthropic.com
2. **FRED API** — fred.stlouisfed.org/docs/api/api_key.html
3. **Tavily API** — tavily.com

---

## Out of Scope

- Email delivery (file output only)
- Web dashboard or UI
- Real-time intraday updates (daily only)
- Automated trade execution (report is input to strategy, not executor)
