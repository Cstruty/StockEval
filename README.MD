# Stock Screening Script Using yFinance

This Python script screens a list of stock tickers using Yahoo Finance data via the `yfinance` library. It calculates several financial metrics, including:

- Return on Capital Employed (ROCE)
- Interest Coverage Ratio
- Gross Margin
- Net Margin
- Cash Conversion Ratio (Operating Cash Flow / Net Income)

Based on these metrics, it calculates an overall score (0–100) for each stock and exports the results to a color-coded HTML file (`screened_stocks.html`).

The web interface uses a small React single-page application served by Flask. The home page features a watchlist where you can search for tickers, fetch their metrics, and view results in a table. Navigation between the home, tools, and about pages is handled on the client side using React Router.

---

## Requirements

- Python 3.7 or newer
- `yfinance`
- `pandas`

---

## Installation
Install dependencies with pip:
```bash
pip install -r requirements.txt
```

### Running the App
Start the Flask server:

```bash
python app.py
```

The console shows search queries and evaluations for troubleshooting.

## Updating Ticker List
The application now downloads the latest list of U.S. and Canadian tickers at
startup using `fetch_latest_tickers()` in `ticker_fetcher.py`. The function
retrieves ticker data from the MarketCap API. If the download fails, it falls
back to the cached `tickers.csv` file.

`fetch_latest_tickers()` expects the JSON response to include the fields
`symbol`, `name`, `is_etf` and `exchange`. The script then queries Yahoo
Finance for each ticker to obtain the current market cap, which is added to the
resulting DataFrame.
