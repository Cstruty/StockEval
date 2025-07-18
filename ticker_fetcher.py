import io
import pandas as pd
import requests

US_URL = "https://dumbstockapi.com/stock?exchanges=NYSE,NASDAQ,AMEX&format=csv"
CA_URL = "https://dumbstockapi.com/stock?exchanges=TSX,TSXV&format=csv"


def _download_csv(url):
    """Download a CSV file and return a DataFrame."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text))


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

        # Normalize column names that may differ between sources
        mapping = {col.lower().strip(): col for col in df.columns}
        symbol_col = mapping.get("symbol")
        name_col = mapping.get("name")
        cap_col = mapping.get("marketcap") or mapping.get("market cap")
        exchange_col = mapping.get("exchange") or mapping.get("market")

        if not symbol_col or not name_col or not cap_col:
            print(f"Missing columns in {market} data; skipping")
            continue

        sub = df[[symbol_col, name_col, cap_col]].copy()
        sub.columns = ["Symbol", "Name", "Market Cap"]
        sub["Market"] = df[exchange_col] if exchange_col else market
        frames.append(sub)

    if not frames:
        raise RuntimeError("No ticker data could be fetched")

    result = pd.concat(frames, ignore_index=True)

    # Ensure numeric market caps for sorting
    result["Market Cap"] = pd.to_numeric(result["Market Cap"], errors="coerce")
    result = result.dropna(subset=["Market Cap"])

    return result.sort_values("Market Cap", ascending=False).reset_index(drop=True)
