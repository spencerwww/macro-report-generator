import os
import json
import anthropic


def fact_check(report: str, data_bundle: dict) -> str:
    """
    Call Claude claude-sonnet-4-6 to fact-check the report against the raw data bundle.
    Returns the original report with a ## FACT-CHECK & INSIGHTS section appended.
    Uses prompt caching on the system prompt to reduce API costs on daily runs.
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
