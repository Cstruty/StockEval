# ==== Imports & Initialization ====

"""Flask application exposing endpoints for the StockEval web interface."""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
from StockEval import evaluate_single_ticker  # Core stock evaluation logic
from ticker_fetcher import main as fetch_main  # Script used to refresh tickers

app = Flask(__name__)

# Path to the cached ticker list
TICKERS_CSV = "tickers.csv"
# DataFrame holding all available tickers
ticker_df = pd.DataFrame()

# ==== Helpers ====

def is_file_older_than_months(file_path, months):
    """Check if a file's last-modified time is older than N months."""
    if not os.path.exists(file_path):
        return True
    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_time > timedelta(days=30 * months)

# ==== Ticker CSV Initialization ====

try:
    # Refresh tickers if CSV is old, otherwise use cached
    if is_file_older_than_months(TICKERS_CSV, 3):
        print("Ticker CSV is older than 3 months. Refreshing...")
        fetch_main()  # Updates the CSV file
    ticker_df = pd.read_csv(TICKERS_CSV)
except Exception as e:
    print(f"Using cached tickers due to error: {e}")
    if os.path.exists(TICKERS_CSV):
        ticker_df = pd.read_csv(TICKERS_CSV)
    else:
        ticker_df = pd.DataFrame(columns=["Symbol", "Name", "Market", "Market Cap"])  # fallback/empty

# ==== Routes ====

@app.route('/')
def index():
    """Render main watchlist app page."""
    return render_template('index.html')


@app.route('/AboutMe')
def about_me():
    """Render About Me page."""
    return render_template('about.html')


@app.route('/OtherTools')
def other_tools():
    """Render Other Tools page."""
    return render_template('tools.html')

@app.route('/search_ticker')
def search_ticker():
    """
    Ticker search endpoint.
    Returns best matches (top 10, sorted by market cap) for autocomplete.
    """
    query = request.args.get('q', '').lower()
    print(f"Search query: {query}")
    if not query:
        return jsonify([])

    # First, grab tickers whose names or symbols *start* with the query
    starts_with = ticker_df[
        ticker_df['Name'].str.lower().str.startswith(query) |
        ticker_df['Symbol'].str.lower().str.startswith(query)
    ]
    # Then search for tickers that merely *contain* the query and haven't
    # already been matched above
    contains = ticker_df[
        ~ticker_df.index.isin(starts_with.index) & (
            ticker_df['Name'].str.lower().str.contains(query) |
            ticker_df['Symbol'].str.lower().str.contains(query)
        )
    ]
    starts_with = starts_with.sort_values(by='Market Cap', ascending=False)
    contains = contains.sort_values(by='Market Cap', ascending=False)

    # Combine, trim to 10, and add a short country code
    matches = pd.concat([starts_with, contains]).head(10)

    def country_short(c):
        """Return a short country code for display in the UI."""
        if isinstance(c, str):
            if c.lower() == 'canada':
                return 'CAD'
            if c.lower() == 'united states':
                return 'USA'
            return c[:3].upper()  # Fallback to first three characters
        return ''

    matches['CountryShort'] = matches['Country'].apply(country_short)

    # Build JSON response for search box
    filtered = matches[['Name', 'Symbol', 'CountryShort']]
    results = filtered.to_dict(orient='records')
    return jsonify(results)

@app.route('/evaluate/<ticker>')
def evaluate(ticker):
    """Evaluate a ticker and return its data for the table (no AI)."""
    print(f"Evaluating ticker: {ticker}")
    result = evaluate_single_ticker(ticker.upper(), run_ai=False)
    return jsonify(result)

@app.route("/run_qualitative", methods=["POST"])
def run_qualitative():
    """
    POST endpoint to run qualitative (AI) analysis for a list of tickers.
    Used for "AI Analysis" column and batch runs.
    """
    data = request.json
    tickers = data.get("tickers", [])
    print(f"Running qualitative for: {tickers}")
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    results = []
    for ticker in tickers:
        # Run the expensive AI evaluation only when requested by the client
        result = evaluate_single_ticker(ticker.upper(), run_ai=True)
        if "Qualitative" in result:
            results.append({
                "Symbol": result["Symbol"],
                "Qualitative": result["Qualitative"]
            })

    return jsonify(results)

# ==== Run the app ====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
