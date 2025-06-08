# 📈 Stock Screening Script Using yFinance

This Python script analyzes a list of stock tickers using Yahoo Finance data via the `yfinance` library. It calculates several key financial metrics and generates a **color-coded HTML report** that includes both quantitative and (optionally) AI-based qualitative analysis.

---

## 📊 Key Features

- Calculates:
  - **ROCE** (Return on Capital Employed)
  - **Interest Coverage Ratio**
  - **Gross Margin**
  - **Net Margin**
  - **Cash Conversion Ratio** (Operating Cash Flow / Net Income)
  - **Gross Profit to Assets**
  - **P/E Ratio**
- Scores each stock out of 100 based on financial strength
- Optional AI-generated qualitative insights (e.g. "Wide Moat", "Pricing Power")
- Outputs to a clean, color-coded `screened_stocks.html` file

---

## 🛠️ Requirements

- Python 3.7 or newer
- [`yfinance`](https://pypi.org/project/yfinance/)
- [`pandas`](https://pypi.org/project/pandas/)

---

## 💾 Installation

1. **Download Python**  
   [https://www.python.org/downloads/](https://www.python.org/downloads/)

2. **Verify Python is installed**

```bash
python3 --version
Install Dependencies

bash
Copy
Edit
pip install yfinance pandas
🚀 Usage
Prepare tickers.txt

Create a text file named tickers.txt with one stock ticker per line.

To enable qualitative AI analysis, make the first line YESAI:

Example with AI:

nginx
Copy
Edit
YESAI
AAPL
MSFT
GOOGL
Without AI:

nginx
Copy
Edit
AAPL
MSFT
GOOGL
Run the Script

bash
Copy
Edit
python3 screen_stocks.py
View the Results

Open screened_stocks.html in your web browser to view the results.

🧠 Qualitative Analysis (Optional)
If YESAI is specified and a valid API key is configured in the script, the following qualitative factors will be analyzed:

Wide Moat

Scalability

Cash Flow Focus

Low Reinvestment Needs

Pricing Power

Predictability

Organic Growth

Growth Strategy

Color Coding:

✅ Yes → Green

❌ No → Red

Each bullet starts with Yes or No, followed by a short label and explanation.

📁 Output Example
The HTML file contains two sections:

Main Stock Screening Table with financial metrics and scores

Qualitative Analysis (if AI is enabled)

All cells are color-coded to highlight strong vs. weak financials.

🧩 Customization
You can modify:

The scoring system in calculate_score()

The AI prompt or model in ask_qualitative_questions()

The metrics included in the main table

🛟 Troubleshooting
401 Unauthorized?

Check your API key

Ensure you're using a supported free model (e.g., deepseek-chat)

Confirm your key hasn't expired or been revoked

📃 License
This project is open for personal or educational use.

Questions or suggestions? Feel free to open an issue or contact the author.

css
Copy
Edit

Let me know if you want to include a badge (e.g. Python version, license, etc.) or a sample image of the HTML output.










Tools



ChatGPT can 
