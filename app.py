from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import init_db, get_db, reset_account
from services.stock_service import (
    get_stock_info, get_stock_history, get_recommendations,
    get_recommendation_summary, get_financials, search_stocks, get_market_overview,
    get_options_expirations, get_options_chain
)
from services.trading_service import (
    get_account, get_portfolio, get_trade_history,
    place_trade, get_portfolio_summary,
    place_options_trade, get_options_portfolio, get_options_trade_history,
    create_order, get_active_orders, get_order_history, cancel_order, check_orders
)
from services.backtest_service import run_backtest, get_available_strategies
from services.advisor_service import get_technical_analysis, get_full_advice
from services.scanner_service import get_todays_picks, get_trade_plan, scan_stocks
import json

app = Flask(__name__)
app.secret_key = 'elephante-stock-analyzer-2026'

init_db()


# ── Page Routes ──────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/stock/<ticker>')
def stock_detail(ticker):
    return render_template('stock.html', ticker=ticker.upper())


@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')


@app.route('/backtest')
def backtest():
    strategies = get_available_strategies()
    return render_template('backtest.html', strategies=strategies)


@app.route('/advisor')
def advisor():
    return render_template('advisor.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


# ── API: Stock Data ──────────────────────────────────────────────────────

@app.route('/api/stock/<ticker>')
def api_stock_info(ticker):
    info = get_stock_info(ticker)
    if info:
        return jsonify(info)
    return jsonify({'error': f'Stock {ticker} not found'}), 404


@app.route('/api/stock/<ticker>/history')
def api_stock_history(ticker):
    period = request.args.get('period', '1y')
    interval = request.args.get('interval', '1d')
    data = get_stock_history(ticker, period=period, interval=interval)
    return jsonify(data)


@app.route('/api/stock/<ticker>/recommendations')
def api_recommendations(ticker):
    recs = get_recommendations(ticker)
    summary = get_recommendation_summary(ticker)
    return jsonify({'recommendations': recs, 'summary': summary})


@app.route('/api/stock/<ticker>/financials')
def api_financials(ticker):
    data = get_financials(ticker)
    return jsonify(data)


@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if len(query) < 1:
        return jsonify([])
    results = search_stocks(query)
    return jsonify(results)


@app.route('/api/market/overview')
def api_market_overview():
    data = get_market_overview()
    return jsonify(data)


# ── API: Watchlist ───────────────────────────────────────────────────────

@app.route('/api/watchlist', methods=['GET'])
def api_get_watchlist():
    conn = get_db()
    items = conn.execute("SELECT * FROM watchlist ORDER BY added_date DESC").fetchall()
    conn.close()
    result = []
    for item in items:
        item_dict = dict(item)
        info = get_stock_info(item_dict['ticker'])
        if info:
            item_dict.update({
                'name': info['name'],
                'price': info['price'],
                'change': info['change'],
                'change_percent': info['change_percent'],
            })
        result.append(item_dict)
    return jsonify(result)


@app.route('/api/watchlist', methods=['POST'])
def api_add_watchlist():
    data = request.get_json()
    ticker = data.get('ticker', '').upper().strip()
    notes = data.get('notes', '')

    if not ticker:
        return jsonify({'error': 'Ticker is required'}), 400

    info = get_stock_info(ticker)
    if not info:
        return jsonify({'error': f'Could not find stock {ticker}'}), 404

    conn = get_db()
    try:
        conn.execute("INSERT INTO watchlist (ticker, notes) VALUES (?, ?)", (ticker, notes))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'{ticker} added to watchlist'})
    except Exception:
        conn.close()
        return jsonify({'error': f'{ticker} is already in your watchlist'}), 409


@app.route('/api/watchlist/<ticker>', methods=['DELETE'])
def api_remove_watchlist(ticker):
    conn = get_db()
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'{ticker.upper()} removed from watchlist'})


# ── API: Paper Trading ───────────────────────────────────────────────────

@app.route('/api/trade', methods=['POST'])
def api_trade():
    data = request.get_json()
    ticker = data.get('ticker', '')
    action = data.get('action', '')
    quantity = float(data.get('quantity', 0))
    notes = data.get('notes', '')

    result = place_trade(ticker, action, quantity, notes)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/portfolio')
def api_portfolio():
    summary = get_portfolio_summary()
    return jsonify(summary)


@app.route('/api/trades')
def api_trades():
    ticker = request.args.get('ticker')
    limit = int(request.args.get('limit', 50))
    trades = get_trade_history(ticker=ticker, limit=limit)
    return jsonify(trades)


@app.route('/api/account/reset', methods=['POST'])
def api_reset_account():
    data = request.get_json() or {}
    balance = float(data.get('balance', 100000))
    reset_account(balance)
    return jsonify({'success': True, 'message': f'Account reset with ${balance:,.2f}'})


# ── API: Orders (Stop Loss / Take Profit / Trailing Stop) ────────────────

@app.route('/api/orders', methods=['GET'])
def api_get_orders():
    return jsonify(get_active_orders())


@app.route('/api/orders/history')
def api_order_history():
    limit = int(request.args.get('limit', 50))
    return jsonify(get_order_history(limit=limit))


@app.route('/api/orders', methods=['POST'])
def api_create_order():
    data = request.get_json()
    result = create_order(
        ticker=data.get('ticker', ''),
        order_type=data.get('order_type', ''),
        action=data.get('action', ''),
        quantity=float(data.get('quantity', 0)),
        trigger_price=float(data['trigger_price']) if data.get('trigger_price') else None,
        trail_percent=float(data['trail_percent']) if data.get('trail_percent') else None,
        notes=data.get('notes', ''),
    )
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def api_cancel_order(order_id):
    result = cancel_order(order_id)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/orders/check', methods=['POST'])
def api_check_orders():
    result = check_orders()
    return jsonify(result)


# ── API: Options ─────────────────────────────────────────────────────────

@app.route('/api/stock/<ticker>/options/expirations')
def api_options_expirations(ticker):
    expirations = get_options_expirations(ticker)
    return jsonify(expirations)


@app.route('/api/stock/<ticker>/options')
def api_options_chain(ticker):
    expiration = request.args.get('expiration', '')
    if not expiration:
        expirations = get_options_expirations(ticker)
        if not expirations:
            return jsonify({'error': 'No options available for this stock'}), 404
        expiration = expirations[0]

    chain = get_options_chain(ticker, expiration)
    if not chain:
        return jsonify({'error': f'Could not load options for {ticker} exp {expiration}'}), 404
    return jsonify(chain)


@app.route('/api/options/trade', methods=['POST'])
def api_options_trade():
    data = request.get_json()
    result = place_options_trade(
        ticker=data.get('ticker', ''),
        option_type=data.get('option_type', ''),
        strike=float(data.get('strike', 0)),
        expiration=data.get('expiration', ''),
        action=data.get('action', ''),
        contracts=int(data.get('contracts', 0)),
        premium=float(data['premium']) if data.get('premium') else None,
        notes=data.get('notes', ''),
    )
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/options/portfolio')
def api_options_portfolio():
    return jsonify(get_options_portfolio())


@app.route('/api/options/trades')
def api_options_trades():
    limit = int(request.args.get('limit', 50))
    trades = get_options_trade_history(limit=limit)
    return jsonify(trades)


# ── API: Backtesting ────────────────────────────────────────────────────

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    data = request.get_json()
    ticker = data.get('ticker', '')
    strategy = data.get('strategy', '')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    initial_capital = float(data.get('initial_capital', 10000))

    params = {k: v for k, v in data.items()
              if k not in ('ticker', 'strategy', 'start_date', 'end_date', 'initial_capital')}

    result = run_backtest(ticker, strategy, start_date, end_date, initial_capital, **params)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/strategies')
def api_strategies():
    return jsonify(get_available_strategies())


# ── API: Advisor ─────────────────────────────────────────────────────────

@app.route('/api/advice/<ticker>')
def api_advice(ticker):
    result = get_full_advice(ticker)
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@app.route('/api/scanner/picks')
def api_scanner_picks():
    limit = int(request.args.get('limit', 10))
    picks = get_todays_picks(limit=limit)
    return jsonify(picks)


@app.route('/api/scanner/plan')
def api_scanner_plan():
    plan = get_trade_plan()
    return jsonify(plan)


@app.route('/api/scanner/all')
def api_scanner_all():
    results = scan_stocks()
    return jsonify(results)


# ── API: Settings ────────────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    conn = get_db()
    settings = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return jsonify({s['key']: s['value'] for s in settings})


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.get_json()
    conn = get_db()
    for key, value in data.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ── Error Handlers ───────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error='Internal server error'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
