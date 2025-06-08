import yfinance as yf
import pandas as pd
import requests
import re

# --- Configuration ---
API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Helper Functions ---

def get_current_liabilities(balance_sheet):
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
    try:
        info = ticker_obj.info
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        return pe
    except:
        return 0

def calc_gross_profit_to_assets(ticker_obj):
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

def calculate_score(roce, interest_cov, gross_margin, net_margin, ccr, gp_assets):
    score = 0
    score += max(min((roce / 0.15) * 30, 30), 0)
    score += max(min((interest_cov / 10) * 30, 30), 0)
    score += max(min((gross_margin / 0.40) * 15, 15), 0)
    score += max(min((net_margin / 0.15) * 15, 15), 0)
    score += max(min((ccr / 0.90) * 10, 10), 0)
    score += max(min((gp_assets / 0.3) * 10, 10), 0)
    return min(round(score), 100)

def color_metric(val, good, okay):
    try:
        val_num = float(val.strip('%x'))
    except:
        return val
    color = 'green' if val_num >= good else 'orange' if val_num >= okay else 'red'
    return f'<span style="color:{color}">{val}</span>'

def color_score(val):
    try:
        val_num = float(val.replace('/100', ''))
    except:
        return val
    color = 'green' if val_num >= 80 else 'orange' if val_num >= 50 else 'red'
    return f'<span style="color:{color}">{val}</span>'


def highlight_yes_no(text):
    text = re.sub(r'\bYes\b', '<span style="color:green;font-weight:bold;">Yes</span>', text)
    text = re.sub(r'\bNo\b', '<span style="color:red;font-weight:bold;">No</span>', text)
    return text

def ask_qualitative_questions(ticker, financial_summary):
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
        return "No qualitative analysis available."

def screen_stocks(tickers, run_ai=True):
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
            if div_yield:
                div_yield = f"{round(div_yield, 5)}%"
            else:
                div_yield = "N/A"

            #div_yield = f"{round(div_yield * 100, 2)}%" if div_yield else "N/A"

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
                    qual = highlight_yes_no(qual)
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

# --- Main Execution ---

with open("tickers.txt", "r") as f:
    lines = [line.strip() for line in f if line.strip()]
if lines and lines[0].upper() == "YESAI":
    run_ai_flag = True
    tickers = [line.upper() for line in lines[1:]]
else:
    run_ai_flag = False
    tickers = [line.upper() for line in lines]

results_df, qual_df = screen_stocks(tickers, run_ai=run_ai_flag)

styled = results_df.copy()
for col, good, okay in [
    ("ROCE", 15, 5),
    ("Interest Coverage", 10, 3),
    ("Gross Margin", 30, 15),
    ("Net Margin", 15, 5),
    ("Cash Conversion Ratio (FCF)", 90, 70),
    ("Gross Profit / Assets", 30, 10),
    ("Dividend Yield", 3, 1)
]:
    styled[col] = styled[col].apply(lambda x: color_metric(x, good, okay))
styled["Score"] = styled["Score"].apply(color_score)

main_table_html = styled.to_html(index=False, escape=False)
qual_table_html = qual_df.to_html(index=False, escape=False)

full_html = f"""
<html>
<head>
<title>Stock Screening Results</title>
<style>
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
  th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
<h2>Main Stock Screening Table</h2>
{main_table_html}
<br><br>
<h2>Qualitative Analysis</h2>
{qual_table_html}
</body>
</html>
"""

with open("screened_stocks.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print("Results saved to screened_stocks.html")
