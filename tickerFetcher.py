"""Utilities for downloading and normalizing stock ticker lists."""

import requests
import json
import csv
import pandas as pd
import re
import os

# ==== Helpers ====

def cleanName(name):
    """
    Remove parentheticals and common suffixes (e.g. 'Common Stock', 'Class A') from a company name.
    """
    # Remove anything in parentheses
    name = re.sub(r'\s*\((.*?)\)', '', name)
    # Strip common suffixes that clutter the company name
    name = re.sub(r'\b(Common Stock|Ordinary Shares|Class [A-Z]|ADR|ADS|Units|Warrants)\b', '', name, flags=re.IGNORECASE)
    return name.strip()

# ==== Fetch NASDAQ (US) stocks from Nasdaq API ====

def getNasdaqRows():
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
    jsonToCsv = {
        "Symbol": "symbol",
        "Name": "name",
        "Market Cap": "marketCap",
        "Country": "country",
    }
    cleanedRows = []
    for row in rows:
        if row.get("symbol") and row.get("name"):
            cleanCompanyName = cleanName(row.get("name", ""))
            cleanedRow = {csvCol: row.get(jsonKey, "") for csvCol, jsonKey in jsonToCsv.items()}
            cleanedRow["Name"] = cleanCompanyName
            cleanedRows.append(cleanedRow)
    return cleanedRows

# ==== Fetch TSX (Canada) stocks from TSX Excel sheet ====

def getTsxRows():
    """
    Download and parse the TSX (Toronto Stock Exchange) Excel file.
    Cleans names, finds the market cap column, and returns a list of dicts.
    """
    excelUrl = "https://www.tsx.com/resource/en/571"
    excelPath = "tsx_companies.xlsx"
    headers = {
        "Referer": "https://www.tsx.com/listings/current-market-statistics",
        "User-Agent": "Mozilla/5.0"
    }

    # Download the Excel file
    resp = requests.get(excelUrl, headers=headers, timeout=30)
    with open(excelPath, "wb") as f:
        f.write(resp.content)

    # Use ExcelFile context to ensure file is closed after parsing
    with pd.ExcelFile(excelPath) as xl:
        # Sheet name may change (find the first "TSX Issuers...")
        sheetName = None
        for s in xl.sheet_names:
            if s.startswith("TSX Issuers"):
                sheetName = s
                break
        if not sheetName:
            raise Exception("No TSX Issuers sheet found!")
        df = xl.parse(sheetName, header=9)

    df = df.dropna(axis=1, how="all")
    df = df[df['Root\nTicker'].notna()]

    # Find market cap column dynamically (should start with "Market Cap (C$)")
    capCol = [col for col in df.columns if col.startswith("Market Cap (C$)")]
    capCol = capCol[0] if capCol else None

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "Symbol": str(row['Root\nTicker']).strip(),
            "Name": str(row['Name']).strip(),
            "Market Cap": row.get(capCol, 0) if capCol else 0,
            "Country": "Canada",
        })

    # Delete the Excel file after reading to avoid clutter
    try:
        os.remove(excelPath)
    except Exception as e:
        print(f"Warning: could not delete {excelPath}: {e}")

    return rows

def normalizeName(name):
    """
    Normalize a company name for deduplication: lowercase, no spaces.
    """
    return ''.join(str(name).lower().split())

# ==== Main routine: Download, deduplicate, and write to tickers.csv ====

def main():
    outFields = ["Symbol", "Name", "Market Cap", "Country"]

    # Download both sources
    nasdaqRows = getNasdaqRows()
    tsxRows = getTsxRows()

    dedup = {}

    # Add all NASDAQ/US tickers (US wins unless TSX duplicates)
    for row in nasdaqRows:
        baseSymbol = row["Symbol"].upper()
        normName = normalizeName(row["Name"])
        key = (baseSymbol, normName)
        dedup[key] = dict(row)  # US version by default

    # Add/overwrite with TSX/Canadian tickers (preferred for duplicates)
    for row in tsxRows:
        baseSymbol = row["Symbol"].upper()
        normName = normalizeName(row["Name"])
        key = (baseSymbol, normName)
        dedup[key] = dict(row)  # Canada wins if duplicate

    allRows = []

    # Append ".TO" to Canadian symbols for Yahoo Finance compatibility
    for row in dedup.values():
        if row["Country"].lower() == "canada":
            row["Symbol"] = f"{row['Symbol']}.TO"
        allRows.append(row)

    # Write combined list to tickers.csv
    with open("tickers.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=outFields)
        writer.writeheader()
        writer.writerows(allRows)
    print(f"Saved {len(allRows)} tickers to tickers.csv")

# ==== Run script directly ====

if __name__ == "__main__":
    main()
