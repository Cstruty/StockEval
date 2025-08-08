"""Core stock evaluation logic used by the Flask app."""

import yfinance as yf
import pandas as pd
import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()

# ==== Configuration ====
apiKey = os.getenv("API_KEY")
apiUrl = "https://openrouter.ai/api/v1/chat/completions"

# ==== Metric Calculation Helpers ====

def getCurrentLiabilities(balanceSheet):
    """
    Try to find current liabilities in a balance sheet using common label names.
    """
    possibleKeys = [
        'Current Liabilities',
        'Total Current Liabilities',
        'Total Current Liab',
        'Total Liabilities',
    ]
    for key in possibleKeys:
        if key in balanceSheet.index:
            return balanceSheet.loc[key].values[0]
    return 0

def calcRoce(tickerObj):
    """
    Calculate Return on Capital Employed (ROCE).
    ROCE = Operating Income / (Total Assets - Current Liabilities)
    """
    try:
        fin = tickerObj.financials  # Income statement data
        if fin is None or fin.empty:
            return 0
        ebit = fin.loc['Operating Income'].values[0]  # Earnings before interest and taxes
        balanceSheet = tickerObj.balance_sheet  # Balance sheet data
        if balanceSheet is None or balanceSheet.empty:
            return 0
        totalAssets = balanceSheet.loc['Total Assets'].values[0]
        currentLiabilities = getCurrentLiabilities(balanceSheet)
        capitalEmployed = totalAssets - currentLiabilities
        return ebit / capitalEmployed if capitalEmployed else 0
    except Exception:
        return 0

def calcInterestCoverage(tickerObj):
    """
    Calculate Interest Coverage Ratio.
    Coverage = EBIT / Interest Expense (try multiple possible row names)
    """
    try:
        fin = tickerObj.financials
        if fin is None or fin.empty or 'Operating Income' not in fin.index:
            return 0
        ebit = fin.loc['Operating Income'].dropna().iloc[0]  # EBIT
        possibleLabels = [
            'Interest Expense',
            'Interest Expense Non Operating',
            'Net Interest Income',
            'Total Other Finance Cost'
        ]
        interestExpense = 0
        for label in possibleLabels:
            # Search common rows for interest expense
            if label in fin.index:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    interestExpense = abs(vals.iloc[0])
                    break
        if interestExpense == 0:
            # Try any label with "interest" in name but not "income"
            # As a last resort, scan for any row containing "interest"
            interestRows = [l for l in fin.index if 'interest' in l.lower() and 'income' not in l.lower()]
            for label in interestRows:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    interestExpense = abs(vals.iloc[0])
                    break
        return ebit / interestExpense if interestExpense else 0
    except Exception:
        return 0

def calcNetMargin(tickerObj):
    """
    Calculate Net Margin: Net Income / Revenue (quarterly financials preferred)
    """
    try:
        fin = tickerObj.quarterly_financials  # Prefer more recent quarterly data
        if fin is None or fin.empty:
            return 0
        netIncome = fin.loc['Net Income'].values[0] if 'Net Income' in fin.index else 0
        revenue = fin.loc['Total Revenue'].values[0] if 'Total Revenue' in fin.index else (
            fin.loc['Operating Revenue'].values[0] if 'Operating Revenue' in fin.index else 0
        )
        return netIncome / revenue if revenue else 0
    except Exception:
        return 0

def calcCashConversionRatioTtm(tickerObj):
    """
    Calculate Cash Conversion Ratio (TTM): Operating Cash Flow / Net Income
    """
    try:
        cfQ = tickerObj.quarterly_cashflow
        finQ = tickerObj.quarterly_financials
        if cfQ is None or finQ is None or cfQ.empty or finQ.empty:
            return 0
        # Sum the last four quarters to approximate trailing twelve months
        cfo = (
            cfQ.loc['Operating Cash Flow'].iloc[:4].sum()
            if 'Operating Cash Flow' in cfQ.index
            else 0
        )
        ni = (
            finQ.loc['Net Income'].iloc[:4].sum()
            if 'Net Income' in finQ.index
            else 0
        )
        return cfo / ni if ni else 0
    except Exception:
        return 0

def calcPeRatio(tickerObj):
    """
    Calculate Price/Earnings Ratio using yfinance info dict.
    """
    try:
        info = tickerObj.info
        # Use trailing P/E if available; otherwise fall back to forward P/E
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        return pe
    except Exception:
        return 0

def calcGrossProfitToAssets(tickerObj):
    """
    Calculate Gross Profit / Total Assets.
    """
    try:
        info = tickerObj.info
        balanceSheet = tickerObj.balance_sheet
        if balanceSheet is None or balanceSheet.empty:
            return 0
        totalAssets = balanceSheet.loc['Total Assets'].values[0]
        grossProfit = info.get("grossProfits", None)
        if grossProfit is None or totalAssets == 0:
            return 0
        return grossProfit / totalAssets
    except Exception:
        return 0

def gatherMetrics(tickerObj):
    """Collect commonly used metrics for a ticker.

    This helper centralizes yfinance calls so that individual functions
    don't have to repeat the same lookups.  It returns the raw values used
    for scoring and display.
    """
    info = tickerObj.info
    metrics = {
        "name": info.get("longName", "N/A"),
        "price": info.get("currentPrice", 0),
        "country": info.get("country"),
        # Raw dividend yield is stored as a decimal (e.g. 0.02 for 2%)
        "divYieldRaw": info.get("dividendYield") or 0,
        "peRatio": calcPeRatio(tickerObj),
        "roce": calcRoce(tickerObj),
        "interestCov": calcInterestCoverage(tickerObj),
        "grossMargin": info.get("grossMargins", 0),
        "netMargin": calcNetMargin(tickerObj),
        "ccr": calcCashConversionRatioTtm(tickerObj),
        "gpAssets": calcGrossProfitToAssets(tickerObj),
    }
    return metrics

def buildSummary(metrics):
    """Create a human readable summary string from metric values."""
    return (
        f"""ROCE: {metrics['roce']:.2%}
Interest Coverage: {metrics['interestCov']:.2f}x
Gross Margin: {metrics['grossMargin']:.2%}
Net Margin: {metrics['netMargin']:.2%}
Cash Conversion Ratio: {metrics['ccr']:.2%}
Gross Profit to Assets: {metrics['gpAssets']:.2%}
P/E Ratio: {metrics['peRatio']:.2f}
Dividend Yield: {metrics['divYieldRaw']:.2%}"""
    )

# ==== Scoring and Formatting ====

def calculateScore(roce, interestCov, grossMargin, netMargin, ccr, gpAssets, peRatio, divYield):
    """Composite scoring logic using weighted metrics."""
    score = 0
    # ROCE and interest coverage dominate the score
    score += max(min((roce / 0.15) * 30, 30), 0)
    score += max(min((interestCov / 10) * 30, 30), 0)
    # Profitability and efficiency metrics carry smaller weights
    score += max(min((grossMargin / 0.40) * 10, 10), 0)
    score += max(min((netMargin / 0.15) * 10, 10), 0)
    score += max(min((ccr / 0.90) * 5, 5), 0)
    score += max(min((gpAssets / 0.3) * 5, 5), 0)
    # Cheap valuation and dividend yield round things out
    score += max(min((20 / peRatio) * 5 if peRatio else 0, 5), 0)
    score += max(min((divYield / 0.03) * 5, 5), 0)
    return min(round(score), 100)

def highlight(text):
    """Highlight key terms in the qualitative analysis HTML."""
    # Emphasize yes/no answers from the model
    text = re.sub(r'\bYes\b', r'<span style="color:green;font-weight:bold;">Yes</span>', text)
    text = re.sub(r'\bNo\b', r'<span style="color:red;font-weight:bold;">No</span>', text)

    def colorFinalScore(match):
        scoreStr = match.group(2)
        try:
            score = int(scoreStr.split('/')[0])
            if score >= 7:
                color = 'green'
            elif score >= 5:
                color = 'orange'
            else:
                color = 'red'
            return f'{match.group(1)}<span style="color:{color};font-weight:bold;">{scoreStr}</span>'
        except Exception:
            return match.group(0)

    text = re.sub(r'(?i)(Final Score:\s*)(\d+/8)', colorFinalScore, text)

    def colorConfidence(match):
        confStr = match.group(2).replace('%', '')
        try:
            conf = int(confStr)
            if conf >= 80:
                color = 'green'
            elif conf >= 60:
                color = 'orange'
            else:
                color = 'red'
            return f'{match.group(1)}<span style="color:{color};font-weight:bold;">{match.group(2)}</span>'
        except Exception:
            return match.group(0)

    text = re.sub(r'(?i)(Confidence:\s*)(\d+%?)', colorConfidence, text)
    return text

# ==== AI Qualitative Questions ====

def askQualitativeQuestions(ticker, financialSummary):
    """
    Query OpenRouter/Deepseek API for qualitative questions about the stock, based on summary.
    Returns a formatted string or a default fallback on error.
    """
    prompt = f"""For {ticker}, respond clearly in bullet points.
Each bullet point must start with "Yes" or "No", followed by a short label of the question in parentheses, then a brief explanation.
Do not restate the question.

Then at the end give a final score out of eight.

Answer the following:

1. Does this company have a wide moat? (Wide Moat)
2. Is it highly scalable? (Scalable)
3. Is it focused on cash flow generation? (Cash Flow Focus)
4. Does it have low need for reinvestment (R&D, capex)? (Low Reinvestment)
5. Does it have pricing power? (Pricing Power)
6. Does it show high operating predictability? (Predictability)
7. Is it mainly driven by organic growth? (Organic Growth)
8. Does it have a clear growth strategy? (Growth Strategy)

Also add a confidence metric after the score out 100%
Financial summary:
{financialSummary}

"""
    headers = {
        # Basic headers required by the OpenRouter API
        "Authorization": f"Bearer {apiKey}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Stock Screener App"
    }
    jsonData = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.7,
        "stream": False
    }
    response = requests.post(apiUrl, headers=headers, json=jsonData)
    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return "No qualitative analysis available."
    try:
        resultJson = response.json()
        content = resultJson['choices'][0]['message']['content']
        return content
    except Exception as e:
        print(f"Error parsing response: {e}")
        return "No qualitative analysis available. Most likely too many results ran today. Please try again tomorrow."

# ==== Main Entry: Evaluate One Ticker ====

def evaluateSingleTicker(ticker, runAi=False):
    """
    Main function to evaluate one stock: fetch yfinance data, calculate all metrics and score,
    and run qualitative analysis if requested.
    """
    try:
        stock = yf.Ticker(ticker)
        # Pull and compute all numeric metrics
        metrics = gatherMetrics(stock)
        divYield = (
            f"{metrics['divYieldRaw']:.2f}%"
            if metrics['divYieldRaw']
            else "N/A"
        )
        scoreVal = calculateScore(
            metrics["roce"],
            metrics["interestCov"],
            metrics["grossMargin"],
            metrics["netMargin"],
            metrics["ccr"],
            metrics["gpAssets"],
            metrics["peRatio"],
            metrics["divYieldRaw"],
        )

        summary = buildSummary(metrics)

        qual = ""
        if runAi:
            # Optionally run the slower LLM-based qualitative analysis
            qualResp = askQualitativeQuestions(ticker, summary)
            if qualResp:
                qual = highlight(qualResp.replace('\n', '<br>'))

        return {
            "Symbol": ticker,
            "Company Name": metrics["name"],
            "Country": metrics["country"],
            "Price": f"${metrics['price']:.2f}",
            "Dividend Yield": divYield,
            "P/E Ratio": f"{metrics['peRatio']:.2f}" if metrics['peRatio'] else "N/A",
            "ROCE": f"{round(metrics['roce'] * 100)}%",
            "Interest Coverage": f"{round(metrics['interestCov'])}x",
            "Gross Margin": f"{round(metrics['grossMargin'] * 100)}%",
            "Net Margin": f"{round(metrics['netMargin'] * 100)}%",
            "Cash Conversion Ratio (FCF)": f"{round(metrics['ccr'] * 100)}%",
            "Gross Profit / Assets": f"{round(metrics['gpAssets'] * 100)}%",
            "Score": f"{round(scoreVal)}/100",
            "Qualitative": qual
        }
    except Exception as e:
        print(f"Error evaluating {ticker}: {e}")
        return {"error": str(e)}

# ==== Batch Screener for Many Tickers (Optional) ====

def screenStocks(tickers, runAi=True):
    """
    Evaluate and screen a batch of tickers; return (dataframe, qualitative dataframe).
    """
    screened = []
    qualitativeList = []

    for ticker in tickers:
        print(f"Evaluating {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            metrics = gatherMetrics(stock)
            divYield = (
                f"{round(metrics['divYieldRaw'], 5)}%"
                if metrics['divYieldRaw']
                else "N/A"
            )

            print(
                f"{ticker}: Price=${metrics['price']:.2f}, DivYld={divYield}, "
                f"P/E={metrics['peRatio']:.2f}, ROCE={metrics['roce']:.2%}, "
                f"IntCov={metrics['interestCov']:.2f}, GM={metrics['grossMargin']:.2%}, "
                f"NM={metrics['netMargin']:.2%}, CCR={metrics['ccr']:.2%}, "
                f"GP/Assets={metrics['gpAssets']:.2%}"
            )

            scoreVal = round(
                calculateScore(
                    metrics['roce'],
                    metrics['interestCov'],
                    metrics['grossMargin'],
                    metrics['netMargin'],
                    metrics['ccr'],
                    metrics['gpAssets'],
                    metrics['peRatio'],
                    metrics['divYieldRaw'],
                ),
                2,
            )

            summary = buildSummary(metrics)

            qual = "Qualitative analysis not run."
            if runAi:
                qualResp = askQualitativeQuestions(ticker, summary)
                if qualResp:
                    qual = highlight(qualResp.replace('\n', '<br>'))
                else:
                    qual = "No qualitative analysis available."

            screened.append({
                "Ticker": ticker,
                "Company Name": metrics["name"],
                "Current Price": f"${metrics['price']:.2f}",
                "Dividend Yield": divYield,
                "P/E Ratio": f"{metrics['peRatio']:.2f}" if metrics['peRatio'] else "N/A",
                "ROCE": f"{round(metrics['roce'] * 100)}%",
                "Interest Coverage": f"{round(metrics['interestCov'])}x",
                "Gross Margin": f"{round(metrics['grossMargin'] * 100)}%",
                "Net Margin": f"{round(metrics['netMargin'] * 100)}%",
                "Cash Conversion Ratio (FCF)": f"{round(metrics['ccr'] * 100)}%",
                "Gross Profit / Assets": f"{round(metrics['gpAssets'] * 100)}%",
                "Score": f"{round(scoreVal)}/100",
            })

            qualitativeList.append({
                "Ticker": ticker,
                "Qualitative Analysis": qual,
            })
        except Exception as e:
            print(f"Failed to evaluate {ticker}: {e}")

    dfScreened = pd.DataFrame(screened)
    dfQual = pd.DataFrame(qualitativeList)
    return dfScreened, dfQual
