import pandas as pd
import requests
import io

# URLs for official exchange lists
NASDAQ_URL = "https://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
OTHER_URL = "https://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"

# Yahoo Finance quote endpoint to fetch market caps
YF_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols={}"


def _download_text(url: str) -> str:
    """Download raw text from a URL."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text


def _parse_nasdaq(text: str) -> pd.DataFrame:
    """Parse the NASDAQ listing file."""
    df = pd.read_csv(io.StringIO(text), sep="|")
    df = df[df["Symbol"] != "File Creation Time"]
    df["Market"] = "NASDAQ"
    return df[["Symbol", "Security Name", "Market"]].rename(
        columns={"Security Name": "Name"}
    )


def _parse_other(text: str) -> pd.DataFrame:
    """Parse the NYSE/AMEX listing file."""
    df = pd.read_csv(io.StringIO(text), sep="|")
    df = df[df["ACT Symbol"] != "File Creation Time"]
    return df[["ACT Symbol", "Security Name", "Exchange"]].rename(
        columns={"ACT Symbol": "Symbol", "Security Name": "Name", "Exchange": "Market"}
    )


def _fetch_market_cap(symbol: str):
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


def fetch_exchange_tickers() -> pd.DataFrame:
    """Download and combine tickers from NASDAQ and NYSE/AMEX with market caps."""
    nasdaq_text = _download_text(NASDAQ_URL)
    other_text = _download_text(OTHER_URL)

    nasdaq_df = _parse_nasdaq(nasdaq_text)
    other_df = _parse_other(other_text)

    df = pd.concat([nasdaq_df, other_df], ignore_index=True)

    # Fetch market cap for each symbol
    df["Market Cap"] = df["Symbol"].apply(_fetch_market_cap)
    df["Market Cap"] = pd.to_numeric(df["Market Cap"], errors="coerce")
    df = df.dropna(subset=["Market Cap"])
    return df.sort_values("Market Cap", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    # Example usage: generate a JSON file with the combined data
    tickers = fetch_exchange_tickers()
    tickers.to_json("dumbstock_data.json", orient="records", indent=2)
    print("Saved dumbstock_data.json with", len(tickers), "records")
