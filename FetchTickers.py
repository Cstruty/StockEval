import os
import time
import io
import pandas as pd
import requests

TICKER_CSV_PATH = "tickers.csv"
MAX_FILE_AGE_DAYS = 30

def is_csv_stale(path):
    if not os.path.exists(path):
        return True
    file_age_days = (time.time() - os.path.getmtime(path)) / (60 * 60 * 24)
    return file_age_days > MAX_FILE_AGE_DAYS

def download_us_tickers():
    url = 'https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df[['Symbol', 'Company Name']]
        df.rename(columns={'Company Name': 'Name'}, inplace=True)
        df['Market Cap'] = 0
        df['Country'] = 'USA'   # Mark country
        return df
    except Exception as e:
        print(f"Failed to fetch US tickers: {e}")
        return pd.DataFrame(columns=['Symbol', 'Name', 'Market Cap', 'Country'])


def download_canadian_tickers():
    url = 'https://www.tsx.com/files/trading/interlisted-companies.txt'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        text = r.text.splitlines()

        # Skip first line (date) and any blank or comment lines
        data_lines = [line for line in text[1:] if line.strip() and not line.startswith('#')]
        data_str = '\n'.join(data_lines)

        # Read as tab-delimited CSV
        df = pd.read_csv(io.StringIO(data_str), delimiter='\t')

        # Check columns
        if 'Symbol' not in df.columns or 'Name' not in df.columns:
            raise ValueError("Expected 'Symbol' and 'Name' columns")

        df = df[['Symbol', 'Name']].copy()

        # Replace colon ':' with dot '.'
        df['Symbol'] = df['Symbol'].str.replace(':', '.', regex=False)

        df['Market Cap'] = 0
        df['Country'] = 'Canada'

        return df

    except Exception as e:
        print(f"Failed to fetch or process TSX tickers: {e}")
        return pd.DataFrame(columns=['Symbol', 'Name', 'Market Cap', 'Country'])


def load_ticker_data():
    if is_csv_stale(TICKER_CSV_PATH):
        us = download_us_tickers()
        ca = download_canadian_tickers()

        # Combine with Canadian last, so duplicates are resolved in favor of Canada
        df = pd.concat([us, ca], ignore_index=True)

        # Remove duplicates by 'Symbol', keep last (Canadian if duplicate)
        df.drop_duplicates(subset='Symbol', keep='last', inplace=True)

        df['Market Cap'] = pd.to_numeric(df.get('Market Cap', 0), errors='coerce').fillna(0)
        df.to_csv(TICKER_CSV_PATH, index=False)
    else:
        df = pd.read_csv(TICKER_CSV_PATH)
    # No CSV overwrite if fresh

