from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
from StockEval import evaluate_single_ticker
from ticker_fetcher import  main as fetch_main  # assuming main() is defined in ticker_fetcher

app = Flask(__name__)

TICKERS_CSV = "tickers.csv"
ticker_df = pd.DataFrame()

# Helper to check if file is older than 3 months
def is_file_older_than_months(file_path, months):
    if not os.path.exists(file_path):
        return True
    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_time > timedelta(days=30 * months)

try:
    if is_file_older_than_months(TICKERS_CSV, 3):
        print("Ticker CSV is older than 3 months. Refreshing...")
        fetch_main()  # this should update the CSV as part of main()
    
    ticker_df = pd.read_csv(TICKERS_CSV)

except Exception as e:
    print(f"Using cached tickers due to error: {e}")
    if os.path.exists(TICKERS_CSV):
        ticker_df = pd.read_csv(TICKERS_CSV)
    else:
        # Fallback: empty DataFrame
        ticker_df = pd.DataFrame(columns=["Symbol", "Name", "Market", "Market Cap"])

except Exception as e:
    print(f"Using cached tickers due to error: {e}")
    if os.path.exists(TICKERS_CSV):
        ticker_df = pd.read_csv(TICKERS_CSV)
    else:
        # Columns as expected for search/filtering
        ticker_df = pd.DataFrame(columns=["Symbol", "Name", "Market", "Market Cap"])

# In-memory watchlist to store added stocks temporarily (resets on server restart)
watchlist = []

@app.route('/')
def index():
    # Render main page and pass current watchlist
    return render_template('index.html', watchlist=watchlist)

@app.route('/search_ticker')
def search_ticker():
    # Get query param, lowercase for case-insensitive search
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    # Filter tickers that start with query in either Name or Symbol
    starts_with = ticker_df[
        ticker_df['Name'].str.lower().str.startswith(query) | 
        ticker_df['Symbol'].str.lower().str.startswith(query)
    ]

    # Filter tickers containing query but excluding the starts_with ones
    contains = ticker_df[
        ~ticker_df.index.isin(starts_with.index) & (
            ticker_df['Name'].str.lower().str.contains(query) | 
            ticker_df['Symbol'].str.lower().str.contains(query)
        )
    ]

    # Sort results by Market Cap descending for relevance
    starts_with = starts_with.sort_values(by='Market Cap', ascending=False)
    contains = contains.sort_values(by='Market Cap', ascending=False)

    # Combine and limit to 10 results
    matches = pd.concat([starts_with, contains]).head(10)

    # Clean company names by removing common suffixes like "Common Stock", "ADR", etc.
    matches['Name'] = matches['Name'].str.replace(
        r'\s*\((.*?)\)|\b(Common Stock|Ordinary Shares|Class [A-Z]|ADR|ADS|Units|Warrants)\b',
        '',
        case=False,
        regex=True
    ).str.strip()

    # Map country to short form
    def country_short(c):
        if isinstance(c, str):
            if c.lower() == 'canada':
                return 'CAD'
            if c.lower() == 'united states':
                return 'USA'
            return c[:3].upper()
        return ''

    matches['CountryShort'] = matches['Country'].apply(country_short)

    # Select relevant columns for response
    filtered = matches[['Name', 'Symbol', 'CountryShort']]

    # Convert to list of dicts for JSON serialization
    results = filtered.to_dict(orient='records')
    return jsonify(results)

@app.route('/add', methods=['POST'])
def add_ticker():
    symbol = request.form.get('symbol').upper()
    # Find matching name from ticker_df, safe access by checking existence
    name_row = ticker_df[ticker_df['Symbol'].str.upper() == symbol]
    if name_row.empty:
        return jsonify({"error": "Ticker not found"}), 404
    name = name_row['Name'].values[0]

    # Add to watchlist if not already added
    if not any(stock['symbol'] == symbol for stock in watchlist):
        watchlist.append({'symbol': symbol, 'name': name})

    # Return rendered HTML snippet for the new watchlist row
    return render_template('watchlist_item.html', stock={'symbol': symbol, 'name': name})

@app.route('/delete/<symbol>', methods=['POST'])
def delete_ticker(symbol):
    global watchlist
    # Remove stock from watchlist by symbol
    watchlist = [stock for stock in watchlist if stock['symbol'] != symbol.upper()]
    return jsonify(success=True)

@app.route('/evaluate/<ticker>')
def evaluate(ticker):
    symbol = ticker.upper()
    match = ticker_df[ticker_df['Symbol'].str.upper() == symbol]
    eval_symbol = symbol
    if not match.empty and str(match['Country'].values[0]).lower() == 'canada':
        eval_symbol = f"{symbol}.TO"
    result = evaluate_single_ticker(eval_symbol, run_ai=False)
    return jsonify(result)

@app.route("/run_qualitative", methods=["POST"])
def run_qualitative():
    data = request.json
    tickers = data.get("tickers", [])
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    results = []
    for ticker in tickers:
        # Run evaluation including AI qualitative analysis
        symbol = ticker.upper()
        match = ticker_df[ticker_df['Symbol'].str.upper() == symbol]
        eval_symbol = symbol
        if not match.empty and str(match['Country'].values[0]).lower() == 'canada':
            eval_symbol = f"{symbol}.TO"
        result = evaluate_single_ticker(eval_symbol, run_ai=True)
        if "Qualitative" in result:
            results.append({
                "Symbol": result["Symbol"],
                "Qualitative": result["Qualitative"]
            })

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
