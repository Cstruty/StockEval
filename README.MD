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


1) Download Python and install extensions (macOS)

-Open a terminal
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python 
```
2) Verify python is installed
```bash
python3 --version
```
3) Download yfinance and pandas

```bash
pip install yfinance pandas
