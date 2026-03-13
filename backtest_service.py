import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def run_backtest(ticker, strategy, start_date, end_date, initial_capital=10000, **params):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty or len(hist) < 50:
            return {'success': False, 'error': 'Not enough historical data for this period.'}

        strategies = {
            'sma_crossover': _sma_crossover,
            'rsi': _rsi_strategy,
            'macd': _macd_strategy,
            'bollinger': _bollinger_strategy,
            'buy_and_hold': _buy_and_hold,
        }

        if strategy not in strategies:
            return {'success': False, 'error': f'Unknown strategy: {strategy}'}

        result = strategies[strategy](hist, initial_capital, **params)
        result['ticker'] = ticker.upper()
        result['strategy'] = strategy
        result['start_date'] = start_date
        result['end_date'] = end_date
        result['initial_capital'] = initial_capital
        result['success'] = True

        return result

    except Exception as e:
        return {'success': False, 'error': str(e)}


def _sma_crossover(hist, initial_capital, short_window=20, long_window=50, **kwargs):
    short_window = int(short_window)
    long_window = int(long_window)

    df = hist.copy()
    df['SMA_Short'] = df['Close'].rolling(window=short_window).mean()
    df['SMA_Long'] = df['Close'].rolling(window=long_window).mean()
    df = df.dropna()

    positions = pd.Series(0, index=df.index)
    positions[df['SMA_Short'] > df['SMA_Long']] = 1

    signals_shifted = positions.diff().fillna(0)

    return _simulate_trades(df, signals_shifted, initial_capital, f'SMA {short_window}/{long_window} Crossover')


def _rsi_strategy(hist, initial_capital, rsi_period=14, oversold=30, overbought=70, **kwargs):
    rsi_period = int(rsi_period)
    oversold = float(oversold)
    overbought = float(overbought)

    df = hist.copy()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df = df.dropna()

    signals = pd.Series(0.0, index=df.index)
    in_position = False

    for i in range(1, len(df)):
        if df['RSI'].iloc[i] < oversold and not in_position:
            signals.iloc[i] = 1
            in_position = True
        elif df['RSI'].iloc[i] > overbought and in_position:
            signals.iloc[i] = -1
            in_position = False

    return _simulate_trades(df, signals, initial_capital, f'RSI ({rsi_period}) [{oversold}/{overbought}]')


def _macd_strategy(hist, initial_capital, fast=12, slow=26, signal=9, **kwargs):
    fast = int(fast)
    slow = int(slow)
    signal = int(signal)

    df = hist.copy()
    df['EMA_Fast'] = df['Close'].ewm(span=fast).mean()
    df['EMA_Slow'] = df['Close'].ewm(span=slow).mean()
    df['MACD'] = df['EMA_Fast'] - df['EMA_Slow']
    df['Signal_Line'] = df['MACD'].ewm(span=signal).mean()
    df = df.dropna()

    positions = pd.Series(0, index=df.index)
    positions[df['MACD'] > df['Signal_Line']] = 1
    signals_shifted = positions.diff().fillna(0)

    return _simulate_trades(df, signals_shifted, initial_capital, f'MACD ({fast}/{slow}/{signal})')


def _bollinger_strategy(hist, initial_capital, window=20, num_std=2, **kwargs):
    window = int(window)
    num_std = float(num_std)

    df = hist.copy()
    df['SMA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()
    df['Upper'] = df['SMA'] + (df['STD'] * num_std)
    df['Lower'] = df['SMA'] - (df['STD'] * num_std)
    df = df.dropna()

    signals = pd.Series(0.0, index=df.index)
    in_position = False

    for i in range(1, len(df)):
        if df['Close'].iloc[i] < df['Lower'].iloc[i] and not in_position:
            signals.iloc[i] = 1
            in_position = True
        elif df['Close'].iloc[i] > df['Upper'].iloc[i] and in_position:
            signals.iloc[i] = -1
            in_position = False

    return _simulate_trades(df, signals, initial_capital, f'Bollinger Bands ({window}, {num_std}σ)')


def _buy_and_hold(hist, initial_capital, **kwargs):
    df = hist.copy()
    buy_price = df['Close'].iloc[0]
    sell_price = df['Close'].iloc[-1]
    shares = initial_capital / buy_price
    final_value = shares * sell_price
    total_return = final_value - initial_capital
    return_pct = (total_return / initial_capital) * 100

    equity_curve = []
    for date, row in df.iterrows():
        equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'value': round(shares * row['Close'], 2),
        })

    return {
        'strategy_name': 'Buy & Hold',
        'final_value': round(final_value, 2),
        'total_return': round(total_return, 2),
        'return_percent': round(return_pct, 2),
        'num_trades': 1,
        'win_rate': 100 if total_return > 0 else 0,
        'max_drawdown': round(_calc_max_drawdown([e['value'] for e in equity_curve]), 2),
        'equity_curve': equity_curve,
        'trades': [{
            'date': df.index[0].strftime('%Y-%m-%d'),
            'action': 'BUY',
            'price': round(buy_price, 2),
            'shares': round(shares, 4),
            'value': round(initial_capital, 2),
        }],
        'prices': [{'date': d.strftime('%Y-%m-%d'), 'price': round(r['Close'], 2)} for d, r in df.iterrows()],
    }


def _simulate_trades(df, signals, initial_capital, strategy_name):
    cash = initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(len(df)):
        date = df.index[i]
        price = df['Close'].iloc[i]

        if signals.iloc[i] > 0 and cash > 0:
            shares = cash / price
            trades.append({
                'date': date.strftime('%Y-%m-%d'),
                'action': 'BUY',
                'price': round(price, 2),
                'shares': round(shares, 4),
                'value': round(cash, 2),
            })
            cash = 0
        elif signals.iloc[i] < 0 and shares > 0:
            cash = shares * price
            trades.append({
                'date': date.strftime('%Y-%m-%d'),
                'action': 'SELL',
                'price': round(price, 2),
                'shares': round(shares, 4),
                'value': round(cash, 2),
            })
            shares = 0

        portfolio_val = cash + (shares * price)
        equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'value': round(portfolio_val, 2),
        })

    final_value = cash + (shares * df['Close'].iloc[-1])
    total_return = final_value - initial_capital
    return_pct = (total_return / initial_capital) * 100

    winning_trades = 0
    for i in range(0, len(trades) - 1, 2):
        if i + 1 < len(trades) and trades[i + 1]['value'] > trades[i]['value']:
            winning_trades += 1
    num_round_trips = len(trades) // 2
    win_rate = (winning_trades / num_round_trips * 100) if num_round_trips else 0

    return {
        'strategy_name': strategy_name,
        'final_value': round(final_value, 2),
        'total_return': round(total_return, 2),
        'return_percent': round(return_pct, 2),
        'num_trades': len(trades),
        'win_rate': round(win_rate, 1),
        'max_drawdown': round(_calc_max_drawdown([e['value'] for e in equity_curve]), 2),
        'equity_curve': equity_curve,
        'trades': trades,
        'prices': [{'date': d.strftime('%Y-%m-%d'), 'price': round(r['Close'], 2)} for d, r in df.iterrows()],
    }


def _calc_max_drawdown(values):
    if not values:
        return 0
    peak = values[0]
    max_dd = 0
    for v in values:
        if v > peak:
            peak = v
        dd = ((peak - v) / peak) * 100 if peak else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def get_available_strategies():
    return [
        {
            'id': 'sma_crossover',
            'name': 'SMA Crossover',
            'description': 'Buy when short-term SMA crosses above long-term SMA; sell on cross below.',
            'params': [
                {'name': 'short_window', 'label': 'Short SMA Period', 'default': 20, 'type': 'int'},
                {'name': 'long_window', 'label': 'Long SMA Period', 'default': 50, 'type': 'int'},
            ]
        },
        {
            'id': 'rsi',
            'name': 'RSI Mean Reversion',
            'description': 'Buy when RSI drops below oversold level; sell when it rises above overbought.',
            'params': [
                {'name': 'rsi_period', 'label': 'RSI Period', 'default': 14, 'type': 'int'},
                {'name': 'oversold', 'label': 'Oversold Level', 'default': 30, 'type': 'float'},
                {'name': 'overbought', 'label': 'Overbought Level', 'default': 70, 'type': 'float'},
            ]
        },
        {
            'id': 'macd',
            'name': 'MACD Signal',
            'description': 'Buy when MACD crosses above signal line; sell on cross below.',
            'params': [
                {'name': 'fast', 'label': 'Fast EMA Period', 'default': 12, 'type': 'int'},
                {'name': 'slow', 'label': 'Slow EMA Period', 'default': 26, 'type': 'int'},
                {'name': 'signal', 'label': 'Signal Period', 'default': 9, 'type': 'int'},
            ]
        },
        {
            'id': 'bollinger',
            'name': 'Bollinger Bands',
            'description': 'Buy below lower band; sell above upper band.',
            'params': [
                {'name': 'window', 'label': 'Window', 'default': 20, 'type': 'int'},
                {'name': 'num_std', 'label': 'Std Deviations', 'default': 2, 'type': 'float'},
            ]
        },
        {
            'id': 'buy_and_hold',
            'name': 'Buy & Hold',
            'description': 'Buy at start and hold until end. Benchmark strategy.',
            'params': []
        },
    ]
