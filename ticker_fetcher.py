import requests
import json
import csv

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
    return [
        {csv_col: row.get(json_key, "") for csv_col, json_key in json_to_csv.items()}
        for row in rows if row.get("symbol") and row.get("name")
    ]

def get_tsx_rows():
    CA_URL = "https://dumbstockapi.com/stock?exchanges=TSX&format=csv"
    response = requests.get(CA_URL, timeout=10)
    response.raise_for_status()
    lines = response.text.splitlines()
    reader = csv.DictReader(lines)
    results = []
    for row in reader:
        results.append({
            "Symbol": row.get("ticker", ""),
            "Name": row.get("name", ""),
            "Market Cap": 0,
            "Country": "Canada",
        })
    return results

def main():
    out_fields = ["Symbol", "Name", "Market Cap", "Country"]
    all_rows = get_nasdaq_rows() + get_tsx_rows()
    with open("tickers.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Saved {len(all_rows)} tickers to tickers.csv")

if __name__ == "__main__":
    main()
