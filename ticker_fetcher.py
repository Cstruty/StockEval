import requests
import json
import csv
import pandas as pd
import re
import os

def clean_name(name):
    # Remove parentheses and common suffixes
    name = re.sub(r'\s*\((.*?)\)', '', name)
    name = re.sub(r'\b(Common Stock|Ordinary Shares|Class [A-Z]|ADR|ADS|Units|Warrants)\b', '', name, flags=re.IGNORECASE)
    return name.strip()

def get_nasdaq_rows():
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

def get_tsx_rows():
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

    # Open Excel file context so it closes properly
    with pd.ExcelFile(excel_path) as xl:
        # Find the correct sheet name dynamically
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

    # Find the market cap column dynamically
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

    # Now, after the Excel file is fully closed, delete it
    try:
        os.remove(excel_path)
    except Exception as e:
        print(f"Warning: could not delete {excel_path}: {e}")

    return rows


def normalize_name(name):
    return ''.join(str(name).lower().split())

def main():
    out_fields = ["Symbol", "Name", "Market Cap", "Country"]

    nasdaq_rows = get_nasdaq_rows()
    tsx_rows = get_tsx_rows()

    # Build deduplication dict: key is (bare symbol, name), value is the row


    dedup = {}

    # First add all NASDAQ (US) tickers
    for row in nasdaq_rows:
        base_symbol = row["Symbol"].upper()
        norm_name = normalize_name(row["Name"])
        key = (base_symbol, norm_name)
        dedup[key] = dict(row)  # US version initially

    # Now add all TSX (Canadian) tickers (which should overwrite US if duplicate)
    for row in tsx_rows:
        base_symbol = row["Symbol"].upper()
        norm_name = normalize_name(row["Name"])
        key = (base_symbol, norm_name)
        dedup[key] = dict(row)  # Canadian version will overwrite if match

    all_rows = []
    
    for row in dedup.values():

        if row["Country"].lower() == "canada":
            row["Symbol"] = f"{row['Symbol']}.TO"

        all_rows.append(row)


    with open("tickers.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Saved {len(all_rows)} tickers to tickers.csv")

if __name__ == "__main__":
    main()
