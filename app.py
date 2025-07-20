from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
from StockEval import evaluate_single_ticker
from ticker_fetcher import main as fetch_main

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
        fetch_main()  # update the CSV if needed
    ticker_df = pd.read_csv(TICKERS_CSV)
except Exception as e:
    print(f"Using cached tickers due to error: {e}")
    if os.path.exists(TICKERS_CSV):
        ticker_df = pd.read_csv(TICKERS_CSV)
    else:
        # Columns as expected for search/filtering
        ticker_df = pd.DataFrame(columns=["Symbol", "Name", "Market", "Market Cap"])

@app.route('/')
def index():
    # Render main page
    return render_template('index.html')

@app.route('/search_ticker')
def search_ticker():
    # Get query param, lowercase for case-insensitive search
    query = request.args.get('q', '').lower()
    print(f"Search query: {query}")
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


@app.route('/evaluate/<ticker>')
def evaluate(ticker):
    print(f"Evaluating ticker: {ticker}")
    result = evaluate_single_ticker(ticker.upper(), run_ai=False)
    return jsonify(result)

@app.route("/run_qualitative", methods=["POST"])
def run_qualitative():
    data = request.json
    tickers = data.get("tickers", [])
    print(f"Running qualitative for: {tickers}")
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    results = []
    for ticker in tickers:
        # Run evaluation including AI qualitative analysis
        result = evaluate_single_ticker(ticker.upper(), run_ai=True)
        if "Qualitative" in result:
            results.append({
                "Symbol": result["Symbol"],
                "Qualitative": result["Qualitative"]
            })

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
