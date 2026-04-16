import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from price_fetcher import fetch_prices, fetch_macro


def _mock_ticker(close_values):
    mock = MagicMock()
    mock.history.return_value = pd.DataFrame(
        {"Close": close_values},
        index=pd.to_datetime([f"2026-04-{14 + i}" for i in range(len(close_values))]),
    )
    return mock


def test_fetch_prices_returns_four_categories():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    assert set(result.keys()) == {"equities", "fx", "crypto", "commodities"}


def test_fetch_prices_sp500_present():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    assert "SP500" in result["equities"]


def test_fetch_prices_value_has_required_fields():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([6885.0, 6967.38])):
        result = fetch_prices()
    sp500 = result["equities"]["SP500"]
    assert "value" in sp500
    assert "change_pct" in sp500
    assert "source" in sp500
    assert "symbol" in sp500
    assert "as_of" in sp500


def test_fetch_prices_change_pct_calculation():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([100.0, 105.0])):
        result = fetch_prices()
    sp500 = result["equities"]["SP500"]
    assert sp500["change_pct"] == pytest.approx(5.0, rel=1e-3)


def test_fetch_prices_handles_empty_ticker_gracefully():
    mock = MagicMock()
    mock.history.return_value = pd.DataFrame()
    with patch("price_fetcher.yf.Ticker", return_value=mock):
        result = fetch_prices()
    assert result["equities"]["SP500"]["value"] is None


def test_fetch_prices_all_fx_pairs_present():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([1.14, 1.142])):
        result = fetch_prices()
    for pair in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "DXY"]:
        assert pair in result["fx"], f"{pair} missing from fx"


def test_fetch_prices_all_crypto_present():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([73000.0, 74300.0])):
        result = fetch_prices()
    for asset in ["BTC", "ETH", "XRP", "SOL"]:
        assert asset in result["crypto"], f"{asset} missing from crypto"


def test_fetch_prices_single_row_change_pct_is_none():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([100.0])):
        result = fetch_prices()
    assert result["equities"]["SP500"]["change_pct"] is None


def test_fetch_prices_handles_ticker_exception_gracefully():
    mock = MagicMock()
    mock.history.side_effect = Exception("network error")
    with patch("price_fetcher.yf.Ticker", return_value=mock):
        result = fetch_prices()
    sp500 = result["equities"]["SP500"]
    assert sp500["value"] is None
    assert sp500["change_pct"] is None
    assert sp500["symbol"] == "^GSPC"


def test_fetch_prices_as_of_is_iso_date_string():
    import re
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([100.0, 105.0])):
        result = fetch_prices()
    assert re.match(r"\d{4}-\d{2}-\d{2}", result["equities"]["SP500"]["as_of"])


def test_fetch_prices_all_commodities_present():
    with patch("price_fetcher.yf.Ticker", return_value=_mock_ticker([94.0, 91.0])):
        result = fetch_prices()
    for asset in ["BRENT", "WTI", "GOLD", "SILVER", "COPPER", "NAT_GAS"]:
        assert asset in result["commodities"], f"{asset} missing from commodities"


def test_fetch_macro_returns_required_keys():
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [3.3], index=pd.to_datetime(["2026-03-01"])
    )
    with patch("price_fetcher.Fred", return_value=mock_fred):
        result = fetch_macro()
    for key in ["cpi_yoy", "ppi_mom", "fed_funds", "treasury_10y", "treasury_2y"]:
        assert key in result, f"{key} missing from macro bundle"


def test_fetch_macro_values_have_source_and_url():
    mock_fred = MagicMock()
    mock_fred.get_series.return_value = pd.Series(
        [3.3], index=pd.to_datetime(["2026-03-01"])
    )
    with patch("price_fetcher.Fred", return_value=mock_fred):
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
    with patch("price_fetcher.Fred", return_value=mock_fred):
        result = fetch_macro()
    assert result["cpi_yoy"]["value"] is None


def test_fetch_macro_handles_fred_constructor_failure_gracefully():
    with patch("price_fetcher.Fred", side_effect=Exception("invalid API key")):
        result = fetch_macro()
    for key in ["cpi_yoy", "ppi_mom", "fed_funds", "treasury_10y", "treasury_2y"]:
        assert result[key]["value"] is None
        assert "fred.stlouisfed.org" in result[key]["url"]
