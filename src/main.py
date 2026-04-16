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
