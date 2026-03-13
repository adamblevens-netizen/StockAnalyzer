import yfinance as yf
import numpy as np
from services.stock_service import get_stock_info, get_recommendation_summary


def get_technical_analysis(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='6mo')

        if hist.empty or len(hist) < 50:
            return {'success': False, 'error': 'Not enough data for analysis.'}

        close = hist['Close']
        indicators = {}

        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        ema_12 = close.ewm(span=12).mean().iloc[-1]
        ema_26 = close.ewm(span=26).mean().iloc[-1]
        current_price = close.iloc[-1]

        indicators['sma_20'] = round(sma_20, 2)
        indicators['sma_50'] = round(sma_50, 2)
        indicators['sma_200'] = round(sma_200, 2) if sma_200 else None
        indicators['ema_12'] = round(ema_12, 2)
        indicators['ema_26'] = round(ema_26, 2)

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        indicators['rsi'] = round(rsi, 2)

        macd_line = ema_12 - ema_26
        macd_series = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal_line = macd_series.ewm(span=9).mean().iloc[-1]
        indicators['macd'] = round(macd_line, 4)
        indicators['macd_signal'] = round(signal_line, 4)
        indicators['macd_histogram'] = round(macd_line - signal_line, 4)

        bb_sma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        indicators['bb_upper'] = round((bb_sma + 2 * bb_std).iloc[-1], 2)
        indicators['bb_lower'] = round((bb_sma - 2 * bb_std).iloc[-1], 2)
        indicators['bb_middle'] = round(bb_sma.iloc[-1], 2)

        stoch_low = close.rolling(14).min()
        stoch_high = close.rolling(14).max()
        stoch_k = ((close - stoch_low) / (stoch_high - stoch_low) * 100).iloc[-1]
        indicators['stochastic_k'] = round(stoch_k, 2)

        vol = hist['Volume']
        indicators['avg_volume_20'] = int(vol.tail(20).mean())
        indicators['volume_ratio'] = round(vol.iloc[-1] / vol.tail(20).mean(), 2) if vol.tail(20).mean() > 0 else 0

        returns = close.pct_change().dropna()
        indicators['volatility_20d'] = round(returns.tail(20).std() * np.sqrt(252) * 100, 2)

        score, signals = _calculate_score(indicators, current_price)

        return {
            'success': True,
            'ticker': ticker.upper(),
            'current_price': round(current_price, 2),
            'indicators': indicators,
            'score': score,
            'signals': signals,
            'recommendation': _score_to_recommendation(score),
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def _calculate_score(indicators, price):
    score = 50
    signals = []

    if price > indicators['sma_20']:
        score += 5
        signals.append({'indicator': 'SMA 20', 'signal': 'Bullish', 'detail': f'Price (${price:.2f}) above SMA 20 (${indicators["sma_20"]:.2f})'})
    else:
        score -= 5
        signals.append({'indicator': 'SMA 20', 'signal': 'Bearish', 'detail': f'Price (${price:.2f}) below SMA 20 (${indicators["sma_20"]:.2f})'})

    if price > indicators['sma_50']:
        score += 5
        signals.append({'indicator': 'SMA 50', 'signal': 'Bullish', 'detail': f'Price above SMA 50 (${indicators["sma_50"]:.2f})'})
    else:
        score -= 5
        signals.append({'indicator': 'SMA 50', 'signal': 'Bearish', 'detail': f'Price below SMA 50 (${indicators["sma_50"]:.2f})'})

    if indicators['sma_200']:
        if price > indicators['sma_200']:
            score += 7
            signals.append({'indicator': 'SMA 200', 'signal': 'Bullish', 'detail': f'Price above SMA 200 (${indicators["sma_200"]:.2f}) — long-term uptrend'})
        else:
            score -= 7
            signals.append({'indicator': 'SMA 200', 'signal': 'Bearish', 'detail': f'Price below SMA 200 (${indicators["sma_200"]:.2f}) — long-term downtrend'})

    if indicators['sma_20'] > indicators['sma_50']:
        score += 5
        signals.append({'indicator': 'Golden Cross', 'signal': 'Bullish', 'detail': 'SMA 20 above SMA 50 — bullish momentum'})
    else:
        score -= 3
        signals.append({'indicator': 'Death Cross', 'signal': 'Bearish', 'detail': 'SMA 20 below SMA 50 — bearish momentum'})

    rsi = indicators['rsi']
    if rsi < 30:
        score += 8
        signals.append({'indicator': 'RSI', 'signal': 'Bullish', 'detail': f'RSI at {rsi:.1f} — oversold territory, potential bounce'})
    elif rsi < 45:
        score += 3
        signals.append({'indicator': 'RSI', 'signal': 'Neutral-Bullish', 'detail': f'RSI at {rsi:.1f} — approaching oversold'})
    elif rsi > 70:
        score -= 8
        signals.append({'indicator': 'RSI', 'signal': 'Bearish', 'detail': f'RSI at {rsi:.1f} — overbought territory, potential pullback'})
    elif rsi > 55:
        score -= 2
        signals.append({'indicator': 'RSI', 'signal': 'Neutral-Bearish', 'detail': f'RSI at {rsi:.1f} — approaching overbought'})
    else:
        signals.append({'indicator': 'RSI', 'signal': 'Neutral', 'detail': f'RSI at {rsi:.1f} — neutral zone'})

    if indicators['macd_histogram'] > 0:
        score += 5
        signals.append({'indicator': 'MACD', 'signal': 'Bullish', 'detail': 'MACD above signal line — bullish momentum'})
    else:
        score -= 5
        signals.append({'indicator': 'MACD', 'signal': 'Bearish', 'detail': 'MACD below signal line — bearish momentum'})

    if price < indicators['bb_lower']:
        score += 6
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'Bullish', 'detail': 'Price below lower band — potentially oversold'})
    elif price > indicators['bb_upper']:
        score -= 6
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'Bearish', 'detail': 'Price above upper band — potentially overbought'})
    else:
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'Neutral', 'detail': 'Price within bands — normal range'})

    if indicators['volume_ratio'] > 1.5:
        signals.append({'indicator': 'Volume', 'signal': 'Alert', 'detail': f'Volume {indicators["volume_ratio"]:.1f}x above average — unusual activity'})
    elif indicators['volume_ratio'] < 0.5:
        signals.append({'indicator': 'Volume', 'signal': 'Low', 'detail': f'Volume {indicators["volume_ratio"]:.1f}x below average — low conviction'})

    score = max(0, min(100, score))
    return score, signals


def _score_to_recommendation(score):
    if score >= 75:
        return {'rating': 'Strong Buy', 'color': '#00c853', 'description': 'Technical indicators are overwhelmingly bullish. Multiple signals confirm upward momentum.'}
    elif score >= 60:
        return {'rating': 'Buy', 'color': '#4caf50', 'description': 'Most technical indicators lean bullish. Good entry opportunity with moderate confidence.'}
    elif score >= 45:
        return {'rating': 'Hold', 'color': '#ff9800', 'description': 'Mixed signals — no clear directional bias. Wait for confirmation before acting.'}
    elif score >= 30:
        return {'rating': 'Sell', 'color': '#f44336', 'description': 'Technical indicators lean bearish. Consider reducing position or tightening stops.'}
    else:
        return {'rating': 'Strong Sell', 'color': '#b71c1c', 'description': 'Technical indicators are overwhelmingly bearish. Multiple signals confirm downward pressure.'}


def get_full_advice(ticker):
    analysis = get_technical_analysis(ticker)
    if not analysis.get('success'):
        return analysis

    info = get_stock_info(ticker)
    rec_summary = get_recommendation_summary(ticker)

    if rec_summary:
        total_analysts = sum(rec_summary.values())
        if total_analysts > 0:
            analyst_score = (
                (rec_summary['strong_buy'] * 100 +
                 rec_summary['buy'] * 75 +
                 rec_summary['hold'] * 50 +
                 rec_summary['sell'] * 25 +
                 rec_summary['strong_sell'] * 0)
                / total_analysts
            )
            blended_score = (analysis['score'] * 0.6) + (analyst_score * 0.4)
            analysis['analyst_score'] = round(analyst_score, 1)
            analysis['blended_score'] = round(blended_score, 1)
            analysis['blended_recommendation'] = _score_to_recommendation(blended_score)

    analysis['rec_summary'] = rec_summary
    analysis['stock_info'] = info

    return analysis
