# Élephante — Stock Analyzer & Trading Platform

A comprehensive stock analysis and paper trading application built with Python (Flask) and a modern dark-themed UI.

## Features

- **Dashboard** — Market overview, watchlist, portfolio snapshot, and quick stock lookup
- **Stock Analysis** — Interactive price charts, key statistics, 52-week ranges, P/E ratios, and more
- **Analyst Ratings** — View consensus ratings and recent analyst actions for any stock
- **AI Advisor** — Technical analysis engine scoring stocks on RSI, MACD, SMA crossovers, Bollinger Bands, and volume with blended analyst scores
- **Paper Trading** — Place virtual buy/sell orders with a $100,000 starting balance, track positions and P&L
- **Strategy Backtester** — Test 5 built-in strategies (SMA Crossover, RSI, MACD, Bollinger Bands, Buy & Hold) against historical data with interactive equity curve charts
- **Watchlist** — Follow stocks and monitor price changes
- **Broker Integration** — Alpaca API support (paper + live), with architecture ready for Fidelity, Schwab, and IBKR

## Tech Stack

- **Backend:** Python 3.10+, Flask
- **Data:** yfinance (Yahoo Finance)
- **Database:** SQLite
- **Charts:** Plotly.js
- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **Fonts:** Inter, Playfair Display (Google Fonts)
- **Icons:** Font Awesome 6

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   ```
   http://localhost:5000
   ```

## Usage

### Dashboard
The main dashboard shows market indices (S&P 500, Dow Jones, NASDAQ, Russell 2000, VIX), your watchlist, portfolio snapshot, and recent trades.

### Analyzing a Stock
Search for any stock using the sidebar search (or `Ctrl+K`), or type a ticker in the Quick Lookup box. Click through to see full details including:
- Interactive price chart with multiple timeframes (1W to MAX)
- Key statistics and fundamentals
- Analyst ratings breakdown
- AI-powered technical analysis and advice
- One-click paper trading

### Paper Trading
- Start with $100,000 in virtual cash
- Buy and sell stocks at current market prices
- Track your portfolio performance and trade history
- Reset your account anytime from the Portfolio page

### Backtesting
- Choose a stock, strategy, date range, and initial capital
- Available strategies: SMA Crossover, RSI Mean Reversion, MACD Signal, Bollinger Bands, Buy & Hold
- View equity curves, trade logs, win rates, and max drawdown

### Broker Integration
- **Alpaca:** Full support for paper and live trading via API keys
- **Fidelity:** Analysis only (no public API — use Élephante for research, execute on Fidelity)
- **TD Ameritrade/Schwab & IBKR:** Planned for future releases

## Project Structure

```
Stock Analyzer/
├── app.py                  # Flask application and routes
├── database.py             # SQLite database layer
├── requirements.txt        # Python dependencies
├── elephante.db            # SQLite database (auto-created)
├── services/
│   ├── stock_service.py    # Stock data fetching (yfinance)
│   ├── trading_service.py  # Paper trading engine
│   ├── backtest_service.py # Strategy backtesting
│   └── advisor_service.py  # Technical analysis advisor
├── templates/
│   ├── base.html           # Base layout with navigation
│   ├── dashboard.html      # Main dashboard
│   ├── stock.html          # Stock detail page
│   ├── portfolio.html      # Portfolio & trading
│   ├── backtest.html       # Strategy backtester
│   └── settings.html       # Settings & broker config
└── static/
    ├── css/style.css       # Dark theme stylesheet
    └── js/app.js           # Core JavaScript
```

## Disclaimer

This application is for educational and research purposes only. It does not constitute financial advice. Always do your own research and consult a qualified financial advisor before making investment decisions.
