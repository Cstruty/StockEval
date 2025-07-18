import io
import pandas as pd
import requests

# These endpoints now return only the following columns:
# ticker, name, is_etf, exchange
US_URL = "https://dumbstockapi.com/stock?exchanges=NYSE,NASDAQ,AMEX&format=csv"
CA_URL = "https://dumbstockapi.com/stock?exchanges=TSX,TSXV&format=csv"
YF_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols={}"


def _download_csv(url):
    """Download a CSV file and return a DataFrame."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


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
    """Return ticker information for U.S. and Canadian stocks.

    The result contains Symbol, Name, Market and Market Cap sorted by
    Market Cap descending. If any download fails, that portion is skipped.
    """
    frames = []
    sources = {"US": US_URL, "CA": CA_URL}

    for market, url in sources.items():
        try:
            df = _download_csv(url)
        except Exception as exc:
            print(f"Failed to download {market} tickers: {exc}")
            continue

        # Column names are expected to be ticker, name, is_etf and exchange
        mapping = {col.lower().strip(): col for col in df.columns}
        symbol_col = mapping.get("ticker")
        name_col = mapping.get("name")
        etf_col = mapping.get("is_etf")
        exchange_col = mapping.get("exchange")

        if not symbol_col or not name_col or not exchange_col:
            print(f"Missing columns in {market} data; skipping")
            continue

        sub = df[[symbol_col, name_col, etf_col, exchange_col]].copy()
        sub.columns = ["Symbol", "Name", "is_etf", "Market"]
        frames.append(sub)

    if not frames:
        raise RuntimeError("No ticker data could be fetched")

    result = pd.concat(frames, ignore_index=True)

    # Fetch market caps individually using Yahoo Finance
    result["Market Cap"] = result["Symbol"].apply(_fetch_market_cap)

    # Ensure numeric market caps for sorting
    result["Market Cap"] = pd.to_numeric(result["Market Cap"], errors="coerce")
    result = result.dropna(subset=["Market Cap"])

    return result.sort_values("Market Cap", ascending=False).reset_index(drop=True)
