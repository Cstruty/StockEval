import yfinance as yf
import pandas as pd
import math

# Try to extract current liabilities using multiple possible label variations
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

# Calculate Return on Capital Employed (ROCE) = EBIT / Capital Employed
def calc_roce(ticker_obj):
    try:
        fin = ticker_obj.financials  # Annual income statement
        if fin is None or fin.empty:
            return 0
        ebit = fin.loc['Operating Income'].values[0]

        balance_sheet = ticker_obj.balance_sheet  # Annual balance sheet
        if balance_sheet is None or balance_sheet.empty:
            return 0

        total_assets = balance_sheet.loc['Total Assets'].values[0]
        current_liabilities = get_current_liabilities(balance_sheet)
        capital_employed = total_assets - current_liabilities

        return ebit / capital_employed if capital_employed else 0
    except Exception:
        return 0

def calc_interest_coverage(ticker_obj):
    try:
        fin = ticker_obj.financials
        if fin is None or fin.empty:
            return 0

        if 'Operating Income' not in fin.index:
            return 0

        ebit_series = fin.loc['Operating Income']
        ebit = ebit_series.dropna().iloc[0]

        # Try to find interest expense rows, prioritize exact matches
        possible_interest_labels = [
            'Interest Expense',
            'Interest Expense Non Operating',
            'Net Interest Income',
            'Total Other Finance Cost'
        ]

        interest_expense = 0
        for label in possible_interest_labels:
            if label in fin.index:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    val = vals.iloc[0]
                    if val != 0:
                        interest_expense = abs(val)
                        print(f"Using {label} with value {interest_expense} as interest expense")
                        break

        # Fallback: search any label containing "interest" but exclude those with "income"
        if interest_expense == 0:
            interest_rows = [label for label in fin.index if ('interest' in label.lower()) and ('income' not in label.lower())]
            for label in interest_rows:
                vals = fin.loc[label].dropna()
                if not vals.empty:
                    val = vals.iloc[0]
                    if val != 0:
                        interest_expense = abs(val)
                        print(f"Fallback using {label} with value {interest_expense} as interest expense")
                        break

        if interest_expense == 0:
            print("No valid interest expense found.")
            return 0

        return ebit / interest_expense

    except Exception as e:
        print(f"Interest coverage error: {e}")
        return 0




# Calculate Net Margin = Net Income / Revenue (from latest quarter)
def calc_net_margin(ticker_obj):
    try:
        fin = ticker_obj.quarterly_financials
        if fin is None or fin.empty:
            return 0
        net_income = fin.loc['Net Income'].values[0] if 'Net Income' in fin.index else 0
        if 'Total Revenue' in fin.index:
            total_revenue = fin.loc['Total Revenue'].values[0]
        elif 'Operating Revenue' in fin.index:
            total_revenue = fin.loc['Operating Revenue'].values[0]
        else:
            total_revenue = 0
        return net_income / total_revenue if total_revenue else 0
    except Exception:
        return 0

# Calculate CCR (Cash Conversion Ratio) using TTM = Operating Cash Flow / Net Income
def calc_cash_conversion_ratio_ttm(ticker_obj):
    try:
        cashflow = ticker_obj.cashflow
        financials = ticker_obj.financials

        if cashflow is None or financials is None:
            return 0

        if 'Operating Cash Flow' not in cashflow.index or 'Net Income' not in financials.index:
            return 0

        # Use the most recent annual Operating Cash Flow and Net Income (take the first column)
        cfo_annual = cashflow.loc['Operating Cash Flow'].iloc[0]
        net_income_annual = financials.loc['Net Income'].iloc[0]

        if net_income_annual == 0:
            return 0

        return cfo_annual / net_income_annual

    except Exception:
        return 0


# Calculate a score (0–100) using weighted scaling for each metric
def calculate_score(roce, interest_cov, gross_margin, net_margin, ccr):
    score = 0
    score += max(min((roce / 0.15) * 30, 30), 0)               # ROCE → up to 30 points
    score += max(min((interest_cov / 10) * 30, 30), 0)         # Interest Coverage → up to 30 points
    score += max(min((gross_margin / 0.40) * 15, 15), 0)       # Gross Margin → up to 15 points
    score += max(min((net_margin / 0.15) * 15, 15), 0)         # Net Margin → up to 15 points
    score += max(min((ccr / 0.90) * 10, 10), 0)                # CCR → up to 10 points
    return min(round(score), 100)


# Apply color based on value thresholds (used for HTML styling)
def color_metric(val, good, okay):
    try:
        val_num = float(val.strip('%x'))
    except:
        return val
    if val_num >= good:
        color = 'green'
    elif val_num >= okay:
        color = 'orange'
    else:
        color = 'red'
    return f'<span style=\"color:{color}\">{val}</span>'

# Color the score value (special formatting rule)
def color_score(val):
    try:
        val_num = float(val.strip('/100'))
    except:
        return val
    if val_num >= 80:
        color = 'green'
    elif val_num >= 50:
        color = 'orange'
    else:
        color = 'red'
    return f'<span style=\"color:{color}\">{val}</span>'

# Main loop to screen tickers and calculate metrics
def screen_stocks(tickers):
    screened = []
    for ticker in tickers:
        print(f"Evaluating {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            company_name = info.get("longName", "N/A")
            current_price = info.get("currentPrice", 0)

            # Calculate all metrics
            roce = calc_roce(stock)
            interest_cov = calc_interest_coverage(stock)
            gross_margin = info.get("grossMargins", 0)
            net_margin = calc_net_margin(stock)
            ccr = calc_cash_conversion_ratio_ttm(stock)

            # Show metrics in terminal
            print(f"{ticker}: Price=${current_price:.2f}, ROCE={roce:.3f}, IntCov={interest_cov:.2f}, GM={gross_margin:.2f}, NM={net_margin:.2f}, CCR={ccr:.4f}")

            # Compute overall score
            score_val = round(calculate_score(roce, interest_cov, gross_margin, net_margin, ccr), 2)

            # Format and store the result
            screened.append({
                "Ticker": ticker,
                "Company Name": company_name,
                "Current Price": f"${current_price:.2f}",
                "ROCE": f"{round(roce * 100)}%",
                "Interest Coverage": f"{round(interest_cov)}x",
                "Gross Margin": f"{round(gross_margin * 100)}%",
                "Net Margin": f"{round(net_margin * 100)}%",
                "Cash Conversion Ratio (FCF)": f"{round(ccr * 100)}%",
                "Score": f"{round(score_val)}/100"
            })

        except Exception as e:
            print(f"Failed to evaluate {ticker}: {e}")
    return pd.DataFrame(screened)

# Load tickers from a plain text file
with open("tickers.txt", "r") as f:
    tickers = [line.strip().upper() for line in f if line.strip()]

# Run screening on the loaded tickers
results = screen_stocks(tickers)

# Show result in terminal
print("\nScreened Stocks:")
print(results)

# Format results with color for display in HTML
styled_results = results.copy()
for col, good, okay in [
    ("ROCE", 15, 5),
    ("Interest Coverage", 10, 3),
    ("Gross Margin", 30, 15),
    ("Net Margin", 15, 5),
    ("Cash Conversion Ratio (FCF)", 90, 70)
]:
    styled_results[col] = styled_results[col].apply(lambda x: color_metric(x, good, okay))

# Apply coloring to the score separately
styled_results["Score"] = styled_results["Score"].apply(color_score)

# Export the color-coded table to an HTML file
styled_results.to_html("screened_stocks.html", index=False, escape=False)
print("Results saved to screened_stocks.html")
