# Stock Screening Script Using yFinance

This Python script screens a list of stock tickers using Yahoo Finance data via the `yfinance` library. It calculates several financial metrics, including:

- Return on Capital Employed (ROCE)
- Interest Coverage Ratio
- Gross Margin
- Net Margin
- Cash Conversion Ratio (Operating Cash Flow / Net Income)

Based on these metrics, it calculates an overall score (0–100) for each stock and exports the results to a color-coded HTML file (`screened_stocks.html`).

---

## Requirements

- Python 3.7 or newer
- `yfinance`
- `pandas`

---

## Installation
Go to the official Python website:
https://www.python.org/downloads/

Download Python and (macOS)
-Open a terminal
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

```bash
brew install python 
Verify python is install
python3 --version

Download yfinance and pandas
Open the terminal
```bash
pip install yfinance pandas
---
## Updating Ticker List
The application now downloads the latest list of U.S. and Canadian tickers at startup using `fetch_latest_tickers()` in `ticker_fetcher.py`. If the download fails, it falls back to the cached `tickers.csv` file.

`fetch_latest_tickers()` expects the downloaded CSV to contain the columns `ticker`, `name`, `is_etf` and `exchange`. The script then queries Yahoo Finance for each ticker to obtain the current market cap, which is added to the resulting DataFrame.
