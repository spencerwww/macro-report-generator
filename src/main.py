import os
import sys
import copy
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


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
