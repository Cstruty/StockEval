import json
import sys


def extract_fields(rows):
    """Return list of dicts with selected fields from Nasdaq screener rows."""
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = row.get("symbol")
        name = row.get("name")
        market_cap = row.get("marketCap")
        country = row.get("country")
        if symbol and name:
            selected.append({
                "symbol": symbol,
                "name": name,
                "marketCap": market_cap,
                "country": country,
            })
    return selected


def main(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("rows") if isinstance(data, dict) else data
    if rows is None:
        print("No rows found in JSON", file=sys.stderr)
        sys.exit(1)
    result = extract_fields(rows)
    json.dump(result, sys.stdout, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <nasdaq_json_file>")
        sys.exit(1)
    main(sys.argv[1])
