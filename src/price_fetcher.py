import sys
import os
import yfinance as yf
import pandas as pd
from fredapi import Fred

EQUITY_TICKERS = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "NASDAQ100": "^NDX",
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
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "EURGBP": "EURGBP=X",
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
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
            change_pct = round(((latest - prev) / prev) * 100, 2) if prev is not None else None
            result[name] = {
                "value": round(latest, 4),
                "change_pct": change_pct,
                "source": f"Yahoo Finance ({symbol})",
                "symbol": symbol,
                "as_of": hist.index[-1].strftime("%Y-%m-%d"),
            }
        except Exception as e:
            print(f"[price_fetcher] WARNING: failed to fetch {symbol}: {e}", file=sys.stderr)
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


FRED_SERIES = {
    "cpi_yoy": {
        "series_id": "CPIAUCSL",
        "url": "https://fred.stlouisfed.org/series/CPIAUCSL",
        "description": "CPI All Urban Consumers YoY%",
        "transform": "yoy_pct",
    },
    "ppi_mom": {
        "series_id": "PPIACO",
        "url": "https://fred.stlouisfed.org/series/PPIACO",
        "description": "PPI All Commodities MoM%",
        "transform": "mom_pct",
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
    try:
        fred = Fred(api_key=os.environ["FRED_API_KEY"])
    except Exception as e:
        print(f"[price_fetcher] WARNING: failed to initialise FRED client: {e}", file=sys.stderr)
        return {key: {"value": None, "as_of": None, "source": meta["description"], "url": meta["url"]}
                for key, meta in FRED_SERIES.items()}

    result = {}
    for key, meta in FRED_SERIES.items():
        try:
            series = fred.get_series(meta["series_id"]).dropna()
            transform = meta.get("transform")
            if transform == "yoy_pct":
                # Year-over-year %: compare latest to 12 months prior (monthly series)
                if len(series) < 13:
                    value = None
                else:
                    value = round((float(series.iloc[-1]) / float(series.iloc[-13]) - 1) * 100, 2)
            elif transform == "mom_pct":
                # Month-over-month %: compare latest to prior month
                if len(series) < 2:
                    value = None
                else:
                    value = round((float(series.iloc[-1]) / float(series.iloc[-2]) - 1) * 100, 2)
            else:
                value = round(float(series.iloc[-1]), 4)
            result[key] = {
                "value": value,
                "as_of": series.index[-1].strftime("%Y-%m-%d"),
                "source": meta["description"],
                "url": meta["url"],
            }
        except Exception as e:
            print(f"[price_fetcher] WARNING: failed to fetch FRED series {meta['series_id']}: {e}", file=sys.stderr)
            result[key] = {
                "value": None,
                "as_of": None,
                "source": meta["description"],
                "url": meta["url"],
            }
    return result
