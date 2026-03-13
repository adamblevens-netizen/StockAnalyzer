from database import get_db
from services.stock_service import get_stock_info
from datetime import datetime
import time


def get_account():
    conn = get_db()
    account = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()
    conn.close()
    return dict(account)


def get_portfolio():
    conn = get_db()
    holdings = conn.execute("SELECT * FROM portfolio WHERE quantity > 0 ORDER BY ticker").fetchall()
    conn.close()

    result = []
    total_value = 0
    total_invested = 0

    for h in holdings:
        h = dict(h)
        info = get_stock_info(h['ticker'])
        current_price = info['price'] if info else 0
        market_value = current_price * h['quantity']
        gain_loss = market_value - h['total_invested']
        gain_loss_pct = (gain_loss / h['total_invested'] * 100) if h['total_invested'] else 0

        result.append({
            'ticker': h['ticker'],
            'quantity': h['quantity'],
            'avg_cost': round(h['avg_cost'], 2),
            'total_invested': round(h['total_invested'], 2),
            'current_price': round(current_price, 2),
            'market_value': round(market_value, 2),
            'gain_loss': round(gain_loss, 2),
            'gain_loss_percent': round(gain_loss_pct, 2),
            'name': info['name'] if info else h['ticker'],
        })
        total_value += market_value
        total_invested += h['total_invested']

    return {
        'holdings': result,
        'total_value': round(total_value, 2),
        'total_invested': round(total_invested, 2),
        'total_gain_loss': round(total_value - total_invested, 2),
    }


def get_trade_history(ticker=None, limit=50):
    conn = get_db()
    if ticker:
        trades = conn.execute(
            "SELECT * FROM paper_trades WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?",
            (ticker.upper(), limit)
        ).fetchall()
    else:
        trades = conn.execute(
            "SELECT * FROM paper_trades ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(t) for t in trades]


def place_trade(ticker, action, quantity, notes=''):
    ticker = ticker.upper()
    action = action.upper()

    if action not in ('BUY', 'SELL'):
        return {'success': False, 'error': 'Invalid action. Must be BUY or SELL.'}

    if quantity <= 0:
        return {'success': False, 'error': 'Quantity must be positive.'}

    info = get_stock_info(ticker)
    if not info:
        return {'success': False, 'error': f'Could not find stock {ticker}.'}

    price = info['price']
    if not price or price <= 0:
        return {'success': False, 'error': f'Could not get current price for {ticker}.'}

    total = round(price * quantity, 2)
    conn = get_db()

    try:
        account = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()

        if action == 'BUY':
            if total > account['cash_balance']:
                conn.close()
                return {'success': False, 'error': f'Insufficient funds. Need ${total:,.2f} but only have ${account["cash_balance"]:,.2f}.'}

            conn.execute("UPDATE account SET cash_balance = cash_balance - ? WHERE id = 1", (total,))

            existing = conn.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,)).fetchone()
            if existing:
                new_qty = existing['quantity'] + quantity
                new_invested = existing['total_invested'] + total
                new_avg = new_invested / new_qty
                conn.execute(
                    "UPDATE portfolio SET quantity = ?, avg_cost = ?, total_invested = ? WHERE ticker = ?",
                    (new_qty, new_avg, new_invested, ticker)
                )
            else:
                conn.execute(
                    "INSERT INTO portfolio (ticker, quantity, avg_cost, total_invested) VALUES (?, ?, ?, ?)",
                    (ticker, quantity, price, total)
                )

        elif action == 'SELL':
            existing = conn.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,)).fetchone()
            if not existing or existing['quantity'] < quantity:
                conn.close()
                available = existing['quantity'] if existing else 0
                return {'success': False, 'error': f'Insufficient shares. Have {available} shares of {ticker}.'}

            conn.execute("UPDATE account SET cash_balance = cash_balance + ? WHERE id = 1", (total,))

            new_qty = existing['quantity'] - quantity
            if new_qty <= 0:
                conn.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
            else:
                cost_basis_sold = existing['avg_cost'] * quantity
                new_invested = existing['total_invested'] - cost_basis_sold
                conn.execute(
                    "UPDATE portfolio SET quantity = ?, total_invested = ? WHERE ticker = ?",
                    (new_qty, new_invested, ticker)
                )

        conn.execute(
            "INSERT INTO paper_trades (ticker, action, quantity, price, total, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (ticker, action, quantity, price, total, notes)
        )

        conn.commit()
        updated_account = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()
        conn.close()

        return {
            'success': True,
            'trade': {
                'ticker': ticker,
                'action': action,
                'quantity': quantity,
                'price': price,
                'total': total,
                'cash_remaining': updated_account['cash_balance'],
            },
            'message': f'Successfully {"bought" if action == "BUY" else "sold"} {quantity} shares of {ticker} at ${price:,.2f} (${total:,.2f} total).'
        }

    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}


def place_options_trade(ticker, option_type, strike, expiration, action, contracts, premium=None, notes=''):
    ticker = ticker.upper()
    option_type = option_type.upper()
    action = action.upper()

    if option_type not in ('CALL', 'PUT'):
        return {'success': False, 'error': 'Option type must be CALL or PUT.'}
    if action not in ('BUY', 'SELL'):
        return {'success': False, 'error': 'Action must be BUY or SELL.'}
    if contracts <= 0:
        return {'success': False, 'error': 'Contracts must be positive.'}

    from services.stock_service import get_options_chain
    if premium is None:
        chain = get_options_chain(ticker, expiration)
        if not chain:
            return {'success': False, 'error': f'Could not load options chain for {ticker} exp {expiration}.'}

        side = chain['calls'] if option_type == 'CALL' else chain['puts']
        match = next((o for o in side if abs(o['strike'] - float(strike)) < 0.01), None)
        if not match:
            return {'success': False, 'error': f'Strike ${strike} not found for {ticker} {option_type} {expiration}.'}

        premium = match['ask'] if action == 'BUY' else match['bid']
        if premium <= 0:
            premium = match['last']
        if premium <= 0:
            return {'success': False, 'error': 'No valid premium available for this contract.'}

    total = round(premium * contracts * 100, 2)  # each contract = 100 shares
    conn = get_db()

    try:
        account = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()

        if action == 'BUY':
            if total > account['cash_balance']:
                conn.close()
                return {'success': False, 'error': f'Insufficient funds. Need ${total:,.2f} but only have ${account["cash_balance"]:,.2f}.'}

            conn.execute("UPDATE account SET cash_balance = cash_balance - ? WHERE id = 1", (total,))

            existing = conn.execute(
                "SELECT * FROM options_portfolio WHERE ticker=? AND option_type=? AND strike=? AND expiration=?",
                (ticker, option_type, float(strike), expiration)
            ).fetchone()

            if existing:
                new_contracts = existing['contracts'] + contracts
                new_invested = existing['total_invested'] + total
                new_avg = new_invested / (new_contracts * 100)
                conn.execute(
                    "UPDATE options_portfolio SET contracts=?, avg_premium=?, total_invested=? WHERE id=?",
                    (new_contracts, new_avg, new_invested, existing['id'])
                )
            else:
                conn.execute(
                    "INSERT INTO options_portfolio (ticker, option_type, strike, expiration, contracts, avg_premium, total_invested) VALUES (?,?,?,?,?,?,?)",
                    (ticker, option_type, float(strike), expiration, contracts, premium, total)
                )

        elif action == 'SELL':
            existing = conn.execute(
                "SELECT * FROM options_portfolio WHERE ticker=? AND option_type=? AND strike=? AND expiration=?",
                (ticker, option_type, float(strike), expiration)
            ).fetchone()

            if not existing or existing['contracts'] < contracts:
                conn.close()
                available = existing['contracts'] if existing else 0
                return {'success': False, 'error': f'Insufficient contracts. Have {available} of this option.'}

            conn.execute("UPDATE account SET cash_balance = cash_balance + ? WHERE id = 1", (total,))

            new_contracts = existing['contracts'] - contracts
            if new_contracts <= 0:
                conn.execute("DELETE FROM options_portfolio WHERE id=?", (existing['id'],))
            else:
                cost_sold = existing['avg_premium'] * contracts * 100
                new_invested = existing['total_invested'] - cost_sold
                conn.execute(
                    "UPDATE options_portfolio SET contracts=?, total_invested=? WHERE id=?",
                    (new_contracts, new_invested, existing['id'])
                )

        conn.execute(
            "INSERT INTO options_trades (ticker, option_type, strike, expiration, action, contracts, premium, total, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (ticker, option_type, float(strike), expiration, action, contracts, premium, total, notes)
        )

        conn.commit()
        updated = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()
        conn.close()

        label = f"{ticker} ${strike} {option_type} {expiration}"
        return {
            'success': True,
            'trade': {
                'ticker': ticker, 'option_type': option_type, 'strike': float(strike),
                'expiration': expiration, 'action': action, 'contracts': contracts,
                'premium': premium, 'total': total, 'cash_remaining': updated['cash_balance'],
            },
            'message': f'Successfully {"bought" if action == "BUY" else "sold"} {contracts} {label} @ ${premium:.2f} (${total:,.2f} total).'
        }

    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}


def get_options_portfolio():
    conn = get_db()
    positions = conn.execute("SELECT * FROM options_portfolio WHERE contracts > 0 ORDER BY expiration, ticker").fetchall()
    conn.close()

    result = []
    total_value = 0
    total_invested = 0

    for p in positions:
        p = dict(p)
        from services.stock_service import get_options_chain
        current_premium = p['avg_premium']  # fallback
        try:
            chain = get_options_chain(p['ticker'], p['expiration'])
            if chain:
                side = chain['calls'] if p['option_type'] == 'CALL' else chain['puts']
                match = next((o for o in side if abs(o['strike'] - p['strike']) < 0.01), None)
                if match:
                    current_premium = match['last'] if match['last'] > 0 else (match['bid'] + match['ask']) / 2
        except Exception:
            pass

        market_value = current_premium * p['contracts'] * 100
        gain_loss = market_value - p['total_invested']
        gain_loss_pct = (gain_loss / p['total_invested'] * 100) if p['total_invested'] else 0

        result.append({
            'id': p['id'],
            'ticker': p['ticker'],
            'option_type': p['option_type'],
            'strike': p['strike'],
            'expiration': p['expiration'],
            'contracts': p['contracts'],
            'avg_premium': round(p['avg_premium'], 2),
            'total_invested': round(p['total_invested'], 2),
            'current_premium': round(current_premium, 2),
            'market_value': round(market_value, 2),
            'gain_loss': round(gain_loss, 2),
            'gain_loss_percent': round(gain_loss_pct, 2),
        })
        total_value += market_value
        total_invested += p['total_invested']

    return {
        'positions': result,
        'total_value': round(total_value, 2),
        'total_invested': round(total_invested, 2),
        'total_gain_loss': round(total_value - total_invested, 2),
    }


def get_options_trade_history(limit=50):
    conn = get_db()
    trades = conn.execute(
        "SELECT * FROM options_trades ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(t) for t in trades]


def get_portfolio_summary():
    account = get_account()
    portfolio = get_portfolio()
    options = get_options_portfolio()
    total_portfolio_value = account['cash_balance'] + portfolio['total_value'] + options['total_value']
    total_return = total_portfolio_value - account['initial_balance']
    total_return_pct = (total_return / account['initial_balance'] * 100) if account['initial_balance'] else 0

    return {
        'cash_balance': round(account['cash_balance'], 2),
        'initial_balance': round(account['initial_balance'], 2),
        'holdings_value': portfolio['total_value'],
        'options_value': options['total_value'],
        'total_portfolio_value': round(total_portfolio_value, 2),
        'total_return': round(total_return, 2),
        'total_return_percent': round(total_return_pct, 2),
        'holdings': portfolio['holdings'],
        'options_positions': options['positions'],
        'num_positions': len(portfolio['holdings']),
        'num_options_positions': len(options['positions']),
    }


# ── Orders (Stop Loss / Take Profit / Trailing Stop) ────────

def create_order(ticker, order_type, action, quantity, trigger_price=None, trail_percent=None, notes=''):
    ticker = ticker.upper()
    order_type = order_type.upper()
    action = action.upper()

    if order_type not in ('STOP_LOSS', 'TAKE_PROFIT', 'TRAILING_STOP'):
        return {'success': False, 'error': 'Order type must be STOP_LOSS, TAKE_PROFIT, or TRAILING_STOP.'}
    if action not in ('BUY', 'SELL'):
        return {'success': False, 'error': 'Action must be BUY or SELL.'}
    if quantity <= 0:
        return {'success': False, 'error': 'Quantity must be positive.'}

    if order_type in ('STOP_LOSS', 'TAKE_PROFIT') and (not trigger_price or trigger_price <= 0):
        return {'success': False, 'error': 'Trigger price is required for this order type.'}
    if order_type == 'TRAILING_STOP' and (not trail_percent or trail_percent <= 0):
        return {'success': False, 'error': 'Trail percentage is required for trailing stop orders.'}

    info = get_stock_info(ticker)
    if not info:
        return {'success': False, 'error': f'Could not find stock {ticker}.'}

    current_price = info['price']

    if action == 'SELL':
        conn = get_db()
        existing = conn.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,)).fetchone()
        conn.close()
        if not existing or existing['quantity'] < quantity:
            avail = existing['quantity'] if existing else 0
            return {'success': False, 'error': f'Insufficient shares. Have {avail} of {ticker}.'}

    trail_high = current_price if order_type == 'TRAILING_STOP' else None
    if order_type == 'TRAILING_STOP':
        trigger_price = round(current_price * (1 - trail_percent / 100), 2)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO orders (ticker, order_type, action, quantity, trigger_price, trail_percent, trail_high, notes) VALUES (?,?,?,?,?,?,?,?)",
            (ticker, order_type, action, quantity, trigger_price, trail_percent, trail_high, notes)
        )
        conn.commit()
        order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        type_label = order_type.replace('_', ' ').title()
        if order_type == 'TRAILING_STOP':
            desc = f'{type_label} {trail_percent}% on {quantity} shares of {ticker} (trigger: ${trigger_price:.2f})'
        else:
            desc = f'{type_label} at ${trigger_price:.2f} for {quantity} shares of {ticker}'

        return {
            'success': True,
            'order_id': order_id,
            'message': f'{type_label} order created: {desc}',
        }
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}


def get_active_orders():
    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE status = 'ACTIVE' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    result = []
    for o in orders:
        o = dict(o)
        info = get_stock_info(o['ticker'])
        current_price = info['price'] if info else 0
        distance = 0
        distance_pct = 0
        if current_price and o['trigger_price']:
            distance = current_price - o['trigger_price']
            distance_pct = (distance / current_price * 100) if current_price else 0

        o['current_price'] = round(current_price, 2)
        o['distance'] = round(distance, 2)
        o['distance_percent'] = round(distance_pct, 2)
        o['type_label'] = o['order_type'].replace('_', ' ').title()
        result.append(o)

    return result


def get_order_history(limit=50):
    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE status != 'ACTIVE' ORDER BY triggered_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(o) for o in orders]


def cancel_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ? AND status = 'ACTIVE'", (order_id,)).fetchone()
    if not order:
        conn.close()
        return {'success': False, 'error': 'Order not found or already inactive.'}

    conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {'success': True, 'message': f'Order #{order_id} cancelled.'}


def check_orders():
    """Evaluate all active orders against current prices and trigger any that match."""
    conn = get_db()
    active = conn.execute("SELECT * FROM orders WHERE status = 'ACTIVE'").fetchall()
    conn.close()

    triggered = []
    for order in active:
        order = dict(order)
        info = get_stock_info(order['ticker'])
        if not info or not info['price']:
            continue

        price = info['price']
        should_trigger = False

        if order['order_type'] == 'TRAILING_STOP':
            trail_high = order['trail_high'] or price
            if price > trail_high:
                trail_high = price
                new_trigger = round(price * (1 - order['trail_percent'] / 100), 2)
                conn2 = get_db()
                conn2.execute(
                    "UPDATE orders SET trail_high = ?, trigger_price = ? WHERE id = ?",
                    (trail_high, new_trigger, order['id'])
                )
                conn2.commit()
                conn2.close()
                order['trigger_price'] = new_trigger

            if price <= order['trigger_price']:
                should_trigger = True

        elif order['order_type'] == 'STOP_LOSS':
            if order['action'] == 'SELL' and price <= order['trigger_price']:
                should_trigger = True
            elif order['action'] == 'BUY' and price >= order['trigger_price']:
                should_trigger = True

        elif order['order_type'] == 'TAKE_PROFIT':
            if order['action'] == 'SELL' and price >= order['trigger_price']:
                should_trigger = True
            elif order['action'] == 'BUY' and price <= order['trigger_price']:
                should_trigger = True

        if should_trigger:
            result = place_trade(
                order['ticker'], order['action'], order['quantity'],
                notes=f"[Auto] {order['order_type'].replace('_',' ')} triggered at ${price:.2f}"
            )
            conn2 = get_db()
            if result['success']:
                conn2.execute(
                    "UPDATE orders SET status = 'TRIGGERED', triggered_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), order['id'])
                )
                triggered.append({
                    'order_id': order['id'],
                    'ticker': order['ticker'],
                    'type': order['order_type'],
                    'action': order['action'],
                    'quantity': order['quantity'],
                    'trigger_price': order['trigger_price'],
                    'executed_price': price,
                    'message': result['message'],
                })
            conn2.commit()
            conn2.close()

    return {'triggered': triggered, 'checked': len(active)}
