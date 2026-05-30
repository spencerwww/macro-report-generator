import os
import json
import anthropic


def generate_report(data_bundle: dict, template: str, recent_reports: list[dict] | None = None) -> str:
    """
    Call Claude claude-sonnet-4-6 to synthesise the macro report from the data bundle.
    Uses prompt caching on the system prompt to reduce API costs on daily runs.

    The template is passed UNCHANGED into the system prompt so the prompt remains
    static day-to-day and cache hits actually fire. The {DATE}/{TIME} values are
    passed via the user message instead, where Claude is instructed to substitute them.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    date_str = data_bundle.get("date", "")
    time_str = data_bundle.get("timestamp", "")[:16].replace("T", " ")

    # System prompt uses the raw template — no substitution — so it stays cacheable.
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
- You may be given the previous reports as continuity context in the user message. Do NOT re-report the same news articles or restate unchanged background. When a level or bias is unchanged, say so briefly (e.g. "unchanged from prior session") and focus each section on what is NEW or has CHANGED since those reports.
"""

    # Build continuity block from prior reports (per-run data — stays out of system prompt).
    recent_reports = recent_reports or []
    if recent_reports:
        prior_block = "\n\n".join(
            f"=== PREVIOUS REPORT ({r['date']}) ===\n{r['content']}"
            for r in recent_reports
        )
    else:
        prior_block = "(No previous reports available — this is the first report or earlier reports are missing.)"

    # Per-request variables go in the user message so the system prompt stays static.
    user_content = f"""Generate today's macro report using this data bundle:

{json.dumps(data_bundle, indent=2, default=str)}

Today's date: {date_str}
Report time: {time_str} UTC

In the report header, replace {{DATE}} with {date_str} and {{TIME}} with {time_str}.

PREVIOUS REPORTS (most recent last) — continuity context. Do NOT repeat the same
news articles, background, or framing already covered below. Lead with what is new
or changed since these reports:
{prior_block}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10000,
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
