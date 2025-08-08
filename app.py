# ==== Imports & Initialization ====

"""Flask application exposing endpoints for the StockEval web interface."""

from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
from StockEval import evaluateSingleTicker  # Core stock evaluation logic
from ticker_fetcher import main as fetchMain  # Script used to refresh tickers

app = Flask(__name__)

# Path to the cached ticker list
tickersCsv = "tickers.csv"
# DataFrame holding all available tickers
tickerDf = pd.DataFrame()

# ==== Helpers ====

def isFileOlderThanMonths(filePath, months):
    """Check if a file's last-modified time is older than N months."""
    if not os.path.exists(filePath):
        return True
    fileTime = datetime.fromtimestamp(os.path.getmtime(filePath))
    return datetime.now() - fileTime > timedelta(days=30 * months)

# ==== Ticker CSV Initialization ====

try:
    # Refresh tickers if CSV is old, otherwise use cached
    if isFileOlderThanMonths(tickersCsv, 3):
        print("Ticker CSV is older than 3 months. Refreshing...")
        fetchMain()  # Updates the CSV file
    tickerDf = pd.read_csv(tickersCsv)
except Exception as e:
    print(f"Using cached tickers due to error: {e}")
    if os.path.exists(tickersCsv):
        tickerDf = pd.read_csv(tickersCsv)
    else:
        tickerDf = pd.DataFrame(columns=["Symbol", "Name", "Market", "Market Cap"])  # fallback/empty

# ==== Routes ====

@app.route('/')
def index():
    """Render main watchlist app page."""
    return render_template('index.html')


@app.route('/AboutMe')
def aboutMe():
    """Render About Me page."""
    return render_template('about.html')


@app.route('/OtherTools')
def otherTools():
    """Render Other Tools page."""
    return render_template('tools.html')

@app.route('/search_ticker')
def searchTicker():
    """
    Ticker search endpoint.
    Returns best matches (top 10, sorted by market cap) for autocomplete.
    """
    query = request.args.get('q', '').lower()
    print(f"Search query: {query}")
    if not query:
        return jsonify([])

    # First, grab tickers whose names or symbols *start* with the query
    startsWith = tickerDf[
        tickerDf['Name'].str.lower().str.startswith(query) |
        tickerDf['Symbol'].str.lower().str.startswith(query)
    ]
    # Then search for tickers that merely *contain* the query and haven't
    # already been matched above
    contains = tickerDf[
        ~tickerDf.index.isin(startsWith.index) & (
            tickerDf['Name'].str.lower().str.contains(query) |
            tickerDf['Symbol'].str.lower().str.contains(query)
        )
    ]
    startsWith = startsWith.sort_values(by='Market Cap', ascending=False)
    contains = contains.sort_values(by='Market Cap', ascending=False)

    # Combine, trim to 10, and add a short country code
    matches = pd.concat([startsWith, contains]).head(10)

    def countryShort(c):
        """Return a short country code for display in the UI."""
        if isinstance(c, str):
            if c.lower() == 'canada':
                return 'CAD'
            if c.lower() == 'united states':
                return 'USA'
            return c[:3].upper()  # Fallback to first three characters
        return ''

    matches['CountryShort'] = matches['Country'].apply(countryShort)

    # Build JSON response for search box
    filtered = matches[['Name', 'Symbol', 'CountryShort']]
    results = filtered.to_dict(orient='records')
    return jsonify(results)

@app.route('/evaluate/<ticker>')
def evaluate(ticker):
    """Evaluate a ticker and return its data for the table (no AI)."""
    print(f"Evaluating ticker: {ticker}")
    result = evaluateSingleTicker(ticker.upper(), runAi=False)
    return jsonify(result)

@app.route("/run_qualitative", methods=["POST"])
def runQualitative():
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
        result = evaluateSingleTicker(ticker.upper(), runAi=True)
        if "Qualitative" in result:
            results.append({
                "Symbol": result["Symbol"],
                "Qualitative": result["Qualitative"]
            })

    return jsonify(results)

# ==== Run the app ====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
