import os
import re
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


DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def load_recent_reports(reports_dir: str = "reports", n: int = 2, before_date: str | None = None) -> list[dict]:
    """Load up to n most recent prior report files, oldest first.

    Report files are named YYYY-MM-DD.md. Files matching before_date (today)
    are excluded so a same-day re-run never feeds a report its own output.
    Returns a list of {"date": str, "content": str}, or [] if the directory
    is missing or holds no dated reports (graceful degradation on cold start).
    """
    dir_path = Path(reports_dir)
    if not dir_path.is_dir():
        return []
    if n <= 0:
        return []
    dated = []
    for f in dir_path.iterdir():
        m = DATE_FILE_RE.match(f.name)
        if not m:
            continue
        if before_date is not None and m.group(1) == before_date:
            continue
        dated.append((m.group(1), f))
    dated.sort(key=lambda x: x[0])
    recent = dated[-n:]
    return [{"date": d, "content": f.read_text(encoding="utf-8")} for d, f in recent]


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
