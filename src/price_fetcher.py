import sys
import yfinance as yf
import pandas as pd

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
