import yfinance as yf
import pandas as pd
import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()

# ==== Configuration ====
API_KEY = os.getenv("API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ==== Metric Calculation Helpers ====

def get_current_liabilities(balance_sheet):
    """
    Try to find current liabilities in a balance sheet using common label names.
    """
    possible_keys = [
        'Current Liabilities',
        'Total Current Liabilities',
        'Total Current Liab',
        'Total Liabilities',
    ]
    for key in possible_keys:
        if key in balance_sheet.index:
            return balance_sheet.loc[key].values[0]
    return 0

def calc_roce(ticker_obj):
    """
    Calculate Return on Capital Employed (ROCE).
    ROCE = Operating Income / (Total Assets - Current Liabilities)
    """
    try:
        fin = ticker_obj.financials
        if fin is None or fin.empty:
            return 0
        ebit = fin.loc['Operating Income'].values[0]
        balance_sheet = ticker_obj.balance_sheet
        if balance_sheet is None or balance_sheet.empty:
            return 0
        total_assets = balance_sheet.loc['Total Assets'].values[0]
        current_liabilities = get_current_liabilities(balance_sheet)
        capital_employed = total_assets - current_liabilities
        return ebit / capital_employed if capital_employed else 0
    except:
        return 0

def calc_interest_coverage(ticker_obj):
    """
    Calculate Interest Coverage Ratio.
    Coverage = EBIT / Interest Expense (try multiple possible row names)
    """
    try:
        fin = ticker_obj.financials
        if fin is None or fin.empty or 'Operating Income' not in fin.index:
            return 0
        ebit = fin.loc['Operating Income'].dropna().iloc[0]
        possible_labels = [
            'Interest Expense',
            'Interest Expense Non Operating',
            'Net Interest Income',
            'Total Other Finance Cost'
        ]
        interest_expense = 0
        for label in possible_labels:
            if label in fin.index:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    interest_expense = abs(vals.iloc[0])
                    break
        if interest_expense == 0:
            # Try any label with "interest" in name but not "income"
            interest_rows = [l for l in fin.index if 'interest' in l.lower() and 'income' not in l.lower()]
            for label in interest_rows:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    interest_expense = abs(vals.iloc[0])
                    break
        return ebit / interest_expense if interest_expense else 0
    except:
        return 0

def calc_net_margin(ticker_obj):
    """
    Calculate Net Margin: Net Income / Revenue (quarterly financials preferred)
    """
    try:
        fin = ticker_obj.quarterly_financials
        if fin is None or fin.empty:
            return 0
        net_income = fin.loc['Net Income'].values[0] if 'Net Income' in fin.index else 0
        revenue = fin.loc['Total Revenue'].values[0] if 'Total Revenue' in fin.index else (
            fin.loc['Operating Revenue'].values[0] if 'Operating Revenue' in fin.index else 0
        )
        return net_income / revenue if revenue else 0
    except:
        return 0

def calc_cash_conversion_ratio_ttm(ticker_obj):
    """
    Calculate Cash Conversion Ratio (TTM): Operating Cash Flow / Net Income
    """
    try:
        cashflow = ticker_obj.cashflow
        financials = ticker_obj.financials
        if cashflow is None or financials is None:
            return 0
        cfo = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
        ni = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
        return cfo / ni if ni else 0
    except:
        return 0

def calc_pe_ratio(ticker_obj):
    """
    Calculate Price/Earnings Ratio using yfinance info dict.
    """
    try:
        info = ticker_obj.info
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        return pe
    except:
        return 0

def calc_gross_profit_to_assets(ticker_obj):
    """
    Calculate Gross Profit / Total Assets.
    """
    try:
        info = ticker_obj.info
        balance_sheet = ticker_obj.balance_sheet
        if balance_sheet is None or balance_sheet.empty:
            return 0
        total_assets = balance_sheet.loc['Total Assets'].values[0]
        gross_profit = info.get("grossProfits", None)
        if gross_profit is None or total_assets == 0:
            return 0
        return gross_profit / total_assets
    except:
        return 0

# ==== Scoring and Formatting ====

def calculate_score(roce, interest_cov, gross_margin, net_margin, ccr, gp_assets):
    """
    Composite scoring logic using weighted metrics.
    Caps each sub-score at max value.
    """
    score = 0
    score += max(min((roce / 0.15) * 30, 30), 0)
    score += max(min((interest_cov / 10) * 30, 30), 0)
    score += max(min((gross_margin / 0.40) * 15, 10), 0)
    score += max(min((net_margin / 0.15) * 15, 10), 0)
    score += max(min((ccr / 0.90) * 10, 10), 0)
    score += max(min((gp_assets / 0.3) * 10, 10), 0)
    return min(round(score), 100)

def color_metric(val, good, okay):
    """
    Color code a metric string based on thresholds (for HTML display).
    """
    try:
        val_num = float(val.strip('%x'))
    except:
        return val
    color = 'green' if val_num >= good else 'orange' if val_num >= okay else 'red'
    return f'<span style="color:{color}">{val}</span>'

def color_score(val):
    """
    Color code a score string (out of 100) for HTML display.
    """
    try:
        val_num = float(val.replace('/100', ''))
    except:
        return val
    color = 'green' if val_num >= 80 else 'orange' if val_num >= 50 else 'red'
    return f'<span style="color:{color}">{val}</span>'

def highlight(text):
    """
    Highlight Yes/No, Final Score, and Confidence metrics in AI qualitative text (HTML).
    """
    text = re.sub(r'\bYes\b', r'<span style="color:green;font-weight:bold;">Yes</span>', text)
    text = re.sub(r'\bNo\b', r'<span style="color:red;font-weight:bold;">No</span>', text)

    def color_final_score(match):
        score_str = match.group(2)
        try:
            score = int(score_str.split('/')[0])
            if score >= 7:
                color = 'green'
            elif score >= 5:
                color = 'orange'
            else:
                color = 'red'
            return f'{match.group(1)}<span style="color:{color};font-weight:bold;">{score_str}</span>'
        except:
            return match.group(0)
    text = re.sub(r'(?i)(Final Score:\s*)(\d+/8)', color_final_score, text)

    def color_confidence(match):
        conf_str = match.group(2).replace('%', '')
        try:
            conf = int(conf_str)
            if conf >= 80:
                color = 'green'
            elif conf >= 60:
                color = 'orange'
            else:
                color = 'red'
            return f'{match.group(1)}<span style="color:{color};font-weight:bold;">{match.group(2)}</span>'
        except:
            return match.group(0)
    text = re.sub(r'(?i)(Confidence:\s*)(\d+%?)', color_confidence, text)
    return text

# ==== AI Qualitative Questions ====

def ask_qualitative_questions(ticker, financial_summary):
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
{financial_summary}

"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Stock Screener App"
    }
    json_data = {
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.7,
        "stream": False
    }
    response = requests.post(API_URL, headers=headers, json=json_data)
    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return "No qualitative analysis available."
    try:
        result_json = response.json()
        content = result_json['choices'][0]['message']['content']
        return content
    except Exception as e:
        print(f"Error parsing response: {e}")
        return "No qualitative analysis available. Most likely too many results ran today. Please try again tomorrow."

# ==== Main Entry: Evaluate One Ticker ====

def evaluate_single_ticker(ticker, run_ai=False):
    """
    Main function to evaluate one stock: fetch yfinance data, calculate all metrics and score,
    and run qualitative analysis if requested.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("longName", "N/A")
        price = info.get("currentPrice", 0)
        div_yield = info.get("dividendYield")
        div_yield = f"{div_yield:.2f}%" if div_yield else "N/A"

        pe_ratio = calc_pe_ratio(stock)
        roce = calc_roce(stock)
        interest_cov = calc_interest_coverage(stock)
        gross_margin = info.get("grossMargins", 0)
        net_margin = calc_net_margin(stock)
        ccr = calc_cash_conversion_ratio_ttm(stock)
        gp_assets = calc_gross_profit_to_assets(stock)

        score_val = calculate_score(roce, interest_cov, gross_margin, net_margin, ccr, gp_assets)

        summary = f"""ROCE: {roce:.2%}
Interest Coverage: {interest_cov:.2f}x
Gross Margin: {gross_margin:.2%}
Net Margin: {net_margin:.2%}
Cash Conversion Ratio: {ccr:.2%}
Gross Profit to Assets: {gp_assets:.2%}"""

        qual = ""
        if run_ai:
            qual_resp = ask_qualitative_questions(ticker, summary)
            if qual_resp:
                qual = highlight(qual_resp.replace('\n', '<br>'))

        return {
            "Symbol": ticker,
            "Company Name": name,
            "Country" : info.get("country"),
            "Price": f"${price:.2f}",
            "Dividend Yield": div_yield,
            "P/E Ratio": f"{pe_ratio:.2f}" if pe_ratio else "N/A",
            "ROCE": f"{round(roce * 100)}%",
            "Interest Coverage": f"{round(interest_cov)}x",
            "Gross Margin": f"{round(gross_margin * 100)}%",
            "Net Margin": f"{round(net_margin * 100)}%",
            "Cash Conversion Ratio (FCF)": f"{round(ccr * 100)}%",
            "Gross Profit / Assets": f"{round(gp_assets * 100)}%",
            "Score": f"{round(score_val)}/100",
            "Qualitative": qual
        }
    except Exception as e:
        print(f"Error evaluating {ticker}: {e}")
        return {"error": str(e)}

# ==== Batch Screener for Many Tickers (Optional) ====

def screen_stocks(tickers, run_ai=True):
    """
    Evaluate and screen a batch of tickers; return (dataframe, qualitative dataframe).
    """
    screened = []
    qualitative_list = []

    for ticker in tickers:
        print(f"Evaluating {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get("longName", "N/A")
            price = info.get("currentPrice", 0)
            div_yield = info.get("dividendYield")
            div_yield = f"{round(div_yield, 5)}%" if div_yield else "N/A"

            pe_ratio = calc_pe_ratio(stock)
            roce = calc_roce(stock)
            interest_cov = calc_interest_coverage(stock)
            gross_margin = info.get("grossMargins", 0)
            net_margin = calc_net_margin(stock)
            ccr = calc_cash_conversion_ratio_ttm(stock)
            gp_assets = calc_gross_profit_to_assets(stock)

            print(f"{ticker}: Price=${price:.2f}, DivYld={div_yield}, P/E={pe_ratio:.2f}, ROCE={roce:.2%}, IntCov={interest_cov:.2f}, GM={gross_margin:.2%}, NM={net_margin:.2%}, CCR={ccr:.2%}, GP/Assets={gp_assets:.2%}")

            score_val = round(calculate_score(roce, interest_cov, gross_margin, net_margin, ccr, gp_assets), 2)

            summary = f"""ROCE: {roce:.2%}
Interest Coverage: {interest_cov:.2f}x
Gross Margin: {gross_margin:.2%}
Net Margin: {net_margin:.2%}
Cash Conversion Ratio: {ccr:.2%}
Gross Profit to Assets: {gp_assets:.2%}"""

            qual = "Qualitative analysis not run."
            if run_ai:
                qual_resp = ask_qualitative_questions(ticker, summary)
                if qual_resp:
                    qual = qual_resp.replace('\n', '<br>')
                    qual = highlight(qual)
                else:
                    qual = "No qualitative analysis available."

            screened.append({
                "Ticker": ticker,
                "Company Name": name,
                "Current Price": f"${price:.2f}",
                "Dividend Yield": div_yield,
                "P/E Ratio": f"{pe_ratio:.2f}" if pe_ratio else "N/A",
                "ROCE": f"{round(roce * 100)}%",
                "Interest Coverage": f"{round(interest_cov)}x",
                "Gross Margin": f"{round(gross_margin * 100)}%",
                "Net Margin": f"{round(net_margin * 100)}%",
                "Cash Conversion Ratio (FCF)": f"{round(ccr * 100)}%",
                "Gross Profit / Assets": f"{round(gp_assets * 100)}%",
                "Score": f"{round(score_val)}/100"
            })

            qualitative_list.append({
                "Ticker": ticker,
                "Qualitative Analysis": qual
            })
        except Exception as e:
            print(f"Failed to evaluate {ticker}: {e}")

    df_screened = pd.DataFrame(screened)
    df_qual = pd.DataFrame(qualitative_list)
    return df_screened, df_qual
