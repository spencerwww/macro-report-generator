import os
import sys
import copy
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
    now = datetime.now(timezone.utc)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "prices": copy.deepcopy(prices),
        "macro": copy.deepcopy(macro),
        "news": list(news),
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
