"""Utilities for downloading and normalizing stock ticker lists."""

import requests
import json
import csv
import pandas as pd
import re
import os

# ==== Helpers ====

def clean_name(name):
    """
    Remove parentheticals and common suffixes (e.g. 'Common Stock', 'Class A') from a company name.
    """
    # Remove anything in parentheses
    name = re.sub(r'\s*\((.*?)\)', '', name)
    # Strip common suffixes that clutter the company name
    name = re.sub(r'\b(Common Stock|Ordinary Shares|Class [A-Z]|ADR|ADS|Units|Warrants)\b', '', name, flags=re.IGNORECASE)
    return name.strip()

# ==== Fetch NASDAQ (US) stocks from Nasdaq API ====

def get_nasdaq_rows():
    """
    Download and parse NASDAQ/US stock list from the Nasdaq API.
    Cleans company names, keeps only required fields.
    """
    URL = "https://api.nasdaq.com/api/screener/stocks?download=true"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers, timeout=10)
    response.raise_for_status()
    data = json.loads(response.content)
    rows = data.get("data", {}).get("rows", [])
    json_to_csv = {
        "Symbol": "symbol",
        "Name": "name",
        "Market Cap": "marketCap",
        "Country": "country",
    }
    cleaned_rows = []
    for row in rows:
        if row.get("symbol") and row.get("name"):
            clean_company_name = clean_name(row.get("name", ""))
            cleaned_row = {csv_col: row.get(json_key, "") for csv_col, json_key in json_to_csv.items()}
            cleaned_row["Name"] = clean_company_name
            cleaned_rows.append(cleaned_row)
    return cleaned_rows

# ==== Fetch TSX (Canada) stocks from TSX Excel sheet ====

def get_tsx_rows():
    """
    Download and parse the TSX (Toronto Stock Exchange) Excel file.
    Cleans names, finds the market cap column, and returns a list of dicts.
    """
    excel_url = "https://www.tsx.com/resource/en/571"
    excel_path = "tsx_companies.xlsx"
    headers = {
        "Referer": "https://www.tsx.com/listings/current-market-statistics",
        "User-Agent": "Mozilla/5.0"
    }

    # Download the Excel file
    resp = requests.get(excel_url, headers=headers, timeout=30)
    with open(excel_path, "wb") as f:
        f.write(resp.content)

    # Use ExcelFile context to ensure file is closed after parsing
    with pd.ExcelFile(excel_path) as xl:
        # Sheet name may change (find the first "TSX Issuers...")
        sheet_name = None
        for s in xl.sheet_names:
            if s.startswith("TSX Issuers"):
                sheet_name = s
                break
        if not sheet_name:
            raise Exception("No TSX Issuers sheet found!")
        df = xl.parse(sheet_name, header=9)

    df = df.dropna(axis=1, how="all")
    df = df[df['Root\nTicker'].notna()]

    # Find market cap column dynamically (should start with "Market Cap (C$)")
    cap_col = [col for col in df.columns if col.startswith("Market Cap (C$)")]
    cap_col = cap_col[0] if cap_col else None

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "Symbol": str(row['Root\nTicker']).strip(),
            "Name": str(row['Name']).strip(),
            "Market Cap": row.get(cap_col, 0) if cap_col else 0,
            "Country": "Canada",
        })

    # Delete the Excel file after reading to avoid clutter
    try:
        os.remove(excel_path)
    except Exception as e:
        print(f"Warning: could not delete {excel_path}: {e}")

    return rows

def normalize_name(name):
    """
    Normalize a company name for deduplication: lowercase, no spaces.
    """
    return ''.join(str(name).lower().split())

# ==== Main routine: Download, deduplicate, and write to tickers.csv ====

def main():
    out_fields = ["Symbol", "Name", "Market Cap", "Country"]

    # Download both sources
    nasdaq_rows = get_nasdaq_rows()
    tsx_rows = get_tsx_rows()

    dedup = {}

    # Add all NASDAQ/US tickers (US wins unless TSX duplicates)
    for row in nasdaq_rows:
        base_symbol = row["Symbol"].upper()
        norm_name = normalize_name(row["Name"])
        key = (base_symbol, norm_name)
        dedup[key] = dict(row)  # US version by default

    # Add/overwrite with TSX/Canadian tickers (preferred for duplicates)
    for row in tsx_rows:
        base_symbol = row["Symbol"].upper()
        norm_name = normalize_name(row["Name"])
        key = (base_symbol, norm_name)
        dedup[key] = dict(row)  # Canada wins if duplicate

    all_rows = []

    # Append ".TO" to Canadian symbols for Yahoo Finance compatibility
    for row in dedup.values():
        if row["Country"].lower() == "canada":
            row["Symbol"] = f"{row['Symbol']}.TO"
        all_rows.append(row)

    # Write combined list to tickers.csv
    with open("tickers.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Saved {len(all_rows)} tickers to tickers.csv")

# ==== Run script directly ====

if __name__ == "__main__":
    main()
