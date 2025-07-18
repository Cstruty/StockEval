import pandas as pd
import requests

# Endpoint for pulling ticker data from MarketCap. The API is expected to
# return JSON with at least the fields `symbol`/`ticker`, `name`, and
# `exchange`.
MC_URL = (
    "https://api.marketcap.com/v3/stock/list?exchanges=NYSE,NASDAQ,AMEX,TSX"
)
YF_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols={}"


def _download_json(url):
    """Download JSON data and return the parsed object."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _fetch_market_cap(symbol):
    """Return the market cap for a ticker using Yahoo Finance."""
    try:
        resp = requests.get(YF_QUOTE_URL.format(symbol), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("quoteResponse", {}).get("result", [])
        if results:
            return results[0].get("marketCap")
    except Exception as exc:
        print(f"Failed to fetch market cap for {symbol}: {exc}")
    return None


def fetch_latest_tickers():
    """Return ticker information for U.S. and Canadian stocks via MarketCap.

    The result contains Symbol, Name, Market and Market Cap sorted by
    Market Cap descending. If the download fails, an exception is raised.
    """
    try:
        data = _download_json(MC_URL)
    except Exception as exc:
        raise RuntimeError(f"Failed to download ticker data: {exc}")

    records = data.get("data") if isinstance(data, dict) else data
    rows = []
    for item in records:
        symbol = item.get("symbol") or item.get("ticker")
        name = item.get("name") or item.get("companyName")
        exchange = item.get("exchange")
        if not symbol or not name or not exchange:
            continue
        is_etf = item.get("is_etf") or item.get("etf", False)
        rows.append({
            "Symbol": symbol,
            "Name": name,
            "is_etf": is_etf,
            "Market": exchange,
        })

    if not rows:
        raise RuntimeError("No ticker data could be fetched")

    result = pd.DataFrame(rows)

    # Fetch market caps individually using Yahoo Finance
    result["Market Cap"] = result["Symbol"].apply(_fetch_market_cap)

    # Ensure numeric market caps for sorting
    result["Market Cap"] = pd.to_numeric(result["Market Cap"], errors="coerce")
    result = result.dropna(subset=["Market Cap"])

    return result.sort_values("Market Cap", ascending=False).reset_index(drop=True)
