import yfinance as yf
import numpy as np
import pandas as pd
import requests
from datetime import datetime, date
import time
import json
import os
from database import get_db

SCAN_UNIVERSE = [
    # ── S&P 500 ──────────────────────────────────────────────────────────
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE',
    'AEP', 'AES', 'AFL', 'AIG', 'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK',
    'ALL', 'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN',
    'ANET', 'ANSS', 'AON', 'AOS', 'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO',
    'ATVI', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXP', 'AZO', 'BA', 'BAC', 'BAX',
    'BBWI', 'BBY', 'BDX', 'BEN', 'BF.B', 'BIO', 'BK', 'BKNG', 'BKR', 'BLK',
    'BMY', 'BR', 'BRK.B', 'BRO', 'BSX', 'BWA', 'BXP', 'C', 'CAG', 'CAH',
    'CARR', 'CAT', 'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDAY', 'CDNS', 'CDW',
    'CE', 'CEG', 'CF', 'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL',
    'CLX', 'CMA', 'CMCSA', 'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF',
    'COO', 'COP', 'COST', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP',
    'CSX', 'CTAS', 'CTLT', 'CTRA', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CZR', 'D',
    'DAL', 'DD', 'DE', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DISH',
    'DLR', 'DLTR', 'DOV', 'DOW', 'DPZ', 'DRI', 'DTE', 'DUK', 'DVA', 'DVN',
    'DXC', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EIX', 'EL', 'EMN',
    'EMR', 'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR', 'EQT', 'ES', 'ESS', 'ETN',
    'ETR', 'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG',
    'FAST', 'FBHS', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FIS', 'FISV', 'FITB',
    'FLT', 'FMC', 'FOX', 'FOXA', 'FRC', 'FRT', 'FTNT', 'FTV', 'GD', 'GE',
    'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC', 'GPN',
    'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD', 'HOLX', 'HON',
    'HPE', 'HPQ', 'HRL', 'HSIC', 'HST', 'HSY', 'HUM', 'HWM', 'IBM', 'ICE',
    'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INTC', 'INTU', 'INVH', 'IP',
    'IPG', 'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT',
    'JCI', 'JKHY', 'JNJ', 'JNPR', 'JPM', 'K', 'KDP', 'KEY', 'KEYS', 'KHC',
    'KIM', 'KLAC', 'KMB', 'KMI', 'KMX', 'KO', 'KR', 'L', 'LDOS', 'LEN',
    'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX',
    'LUMN', 'LUV', 'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS',
    'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK',
    'MKC', 'MKTX', 'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MOS', 'MPC',
    'MPWR', 'MRK', 'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTCH',
    'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE',
    'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWL',
    'NWS', 'NWSA', 'NXPI', 'O', 'ODFL', 'OGN', 'OKE', 'OMC', 'ON', 'ORCL',
    'ORLY', 'OTIS', 'OXY', 'PARA', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEAK',
    'PEG', 'PEP', 'PFE', 'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PKI',
    'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA',
    'PSX', 'PTC', 'PVH', 'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE',
    'REG', 'REGN', 'RF', 'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP',
    'ROST', 'RSG', 'RTX', 'SBAC', 'SBNY', 'SBUX', 'SCHW', 'SEE', 'SHW', 'SIVB',
    'SJM', 'SLB', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STT',
    'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG',
    'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TMO', 'TMUS', 'TPR',
    'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO', 'TXN',
    'TXT', 'TYL', 'UAL', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI',
    'USB', 'V', 'VFC', 'VICI', 'VLO', 'VMC', 'VNO', 'VRSK', 'VRSN', 'VRTX',
    'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WBA', 'WBD', 'WDC', 'WEC', 'WELL',
    'WFC', 'WHR', 'WM', 'WMB', 'WMT', 'WRB', 'WRK', 'WST', 'WTW', 'WY',
    'WYNN', 'XEL', 'XOM', 'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZION', 'ZTS',
    # ── Popular non-S&P 500 ──
    'ABNB', 'COIN', 'PLTR', 'SOFI', 'SQ', 'SHOP', 'SNAP', 'UBER',
]

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scanner_cache.json')
CACHE_MAX_AGE = 1800


def _load_disk_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            return data
    except Exception as e:
        print(f"[Scanner] Cache load error: {e}")
    return None


def _save_disk_cache(results):
    try:
        data = {
            'timestamp': time.time(),
            'generated': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'results': results,
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
        print(f"[Scanner] Saved {len(results)} results to disk")
    except Exception as e:
        print(f"[Scanner] Cache save error: {e}")


def _get_yahoo_session():
    """Create an authenticated Yahoo Finance session with crumb token."""
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    try:
        session.get('https://fc.yahoo.com/', allow_redirects=True, timeout=10)
        r = session.get('https://query2.finance.yahoo.com/v1/test/getcrumb', timeout=10)
        crumb = r.text.strip() if r.status_code == 200 else ''
        return session, crumb
    except Exception as e:
        print(f"[Scanner] Session init error: {e}")
        return session, ''


def _fetch_batch_quotes(tickers):
    """Fetch real-time quotes for all tickers in 1-2 HTTP requests via authenticated Yahoo Finance API."""
    session, crumb = _get_yahoo_session()
    if not crumb:
        print("[Scanner] Could not obtain Yahoo Finance crumb token")
        return {}

    results = {}
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        symbols = ','.join(batch)
        try:
            resp = session.get(
                'https://query2.finance.yahoo.com/v7/finance/quote',
                params={'symbols': symbols, 'crumb': crumb},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get('quoteResponse', {}).get('result', [])
                for q in quotes:
                    sym = q.get('symbol', '')
                    if sym:
                        results[sym] = q
                print(f"[Scanner] Batch {i//batch_size + 1}: got {len(quotes)} quotes")
            elif resp.status_code == 429:
                print("[Scanner] Yahoo batch API rate limited (429)")
                break
            else:
                print(f"[Scanner] Yahoo batch API returned {resp.status_code}")
        except Exception as e:
            print(f"[Scanner] Batch quote error: {e}")
            break

    return results


def _score_from_quote(ticker, q):
    """Score a stock from quote data (no historical download needed)."""
    try:
        price = q.get('regularMarketPrice') or q.get('currentPrice', 0)
        prev_close = q.get('regularMarketPreviousClose') or q.get('previousClose', 0)
        if not price or price <= 0:
            return None

        day_change = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
        volume = q.get('regularMarketVolume') or q.get('volume', 0)
        avg_volume = q.get('averageDailyVolume10Day') or q.get('averageVolume', 0) or q.get('averageDailyVolume3Month', 0)
        vol_ratio = volume / avg_volume if avg_volume > 0 else 1.0

        fifty_day = q.get('fiftyDayAverage', 0)
        two_hundred_day = q.get('twoHundredDayAverage', 0)
        fifty_two_high = q.get('fiftyTwoWeekHigh', 0)
        fifty_two_low = q.get('fiftyTwoWeekLow', 0)
        fifty_day_chg = q.get('fiftyDayAverageChangePercent', 0) or 0
        two_hundred_day_chg = q.get('twoHundredDayAverageChangePercent', 0) or 0

        name = q.get('longName') or q.get('shortName') or q.get('displayName') or ticker
        sector = q.get('sector', 'N/A')
        market_cap = q.get('marketCap', 0)

        score = 50
        reasons = []

        # Price vs moving averages
        if fifty_day > 0 and price > fifty_day:
            score += 5
        elif fifty_day > 0:
            score -= 5

        if two_hundred_day > 0 and price > two_hundred_day:
            score += 7
            if fifty_day > two_hundred_day:
                score += 5
                reasons.append('Golden cross — 50-day MA above 200-day MA')
        elif two_hundred_day > 0:
            score -= 7
            if fifty_day > 0 and fifty_day < two_hundred_day:
                score -= 3
                reasons.append('Death cross — 50-day MA below 200-day MA')

        # 52-week range position
        if fifty_two_high > 0 and fifty_two_low > 0:
            range_pos = (price - fifty_two_low) / (fifty_two_high - fifty_two_low) if (fifty_two_high - fifty_two_low) > 0 else 0.5
            if range_pos < 0.2:
                score += 8
                reasons.append(f'Near 52-week low — potential value opportunity')
            elif range_pos < 0.35:
                score += 4
                reasons.append(f'In lower third of 52-week range')
            elif range_pos > 0.9:
                score -= 6
                reasons.append(f'Near 52-week high — extended')
            elif range_pos > 0.75:
                score -= 2

        # Momentum from day change
        if day_change > 3:
            score += 3
            reasons.append(f'Strong day — up {day_change:.1f}%')
        elif day_change < -3:
            score += 2
            reasons.append(f'Sharp dip ({day_change:.1f}%) — potential bounce')
        elif day_change < -5:
            reasons.append(f'Significant selloff ({day_change:.1f}%)')

        # Volume analysis
        if vol_ratio > 2.0:
            reasons.append(f'Unusual volume ({vol_ratio:.1f}x average)')
            if day_change > 0:
                score += 4
            else:
                score -= 2

        # MA momentum
        if fifty_day_chg > 0.05:
            score += 3
            reasons.append(f'Strong uptrend — {fifty_day_chg*100:.1f}% above 50-day avg')
        elif fifty_day_chg < -0.05:
            score += 2
            reasons.append(f'Pullback from 50-day avg ({fifty_day_chg*100:.1f}%)')

        if two_hundred_day_chg > 0.1:
            score += 3
            reasons.append(f'Long-term uptrend intact')
        elif two_hundred_day_chg < -0.1:
            score -= 3

        # Approximate RSI from available data (50-day change as proxy)
        est_rsi = 50 + (fifty_day_chg * 200) if fifty_day_chg else 50
        est_rsi = max(10, min(90, est_rsi))

        score = max(0, min(100, score))

        if score >= 70:
            action = 'BUY'
        elif score >= 55:
            action = 'CONSIDER BUYING'
        elif score >= 45:
            action = 'HOLD'
        elif score >= 30:
            action = 'CONSIDER SELLING'
        else:
            action = 'SELL'

        week_chg = 0
        month_chg = fifty_day_chg * 100 if fifty_day_chg else 0

        return {
            'ticker': ticker,
            'name': name,
            'sector': sector,
            'market_cap': market_cap,
            'price': round(float(price), 2),
            'day_change': round(float(day_change), 2),
            'week_return': round(float(week_chg), 2),
            'month_return': round(float(month_chg), 2),
            'rsi': round(float(est_rsi), 1),
            'macd_histogram': 0,
            'volume_ratio': round(float(vol_ratio), 2),
            'score': round(float(score), 1),
            'action': action,
            'reasons': reasons if reasons else ['No strong signals — neutral outlook'],
        }
    except Exception as e:
        print(f"[Scanner] Score error for {ticker}: {e}")
        return None


def scan_stocks(tickers=None, force=False):
    """Scan stocks using batch quote API (1-2 HTTP requests for all tickers)."""
    cached = _load_disk_cache()
    if not force and cached and cached.get('results'):
        age = time.time() - cached.get('timestamp', 0)
        if age < CACHE_MAX_AGE:
            return {
                'status': 'ok',
                'results': cached['results'],
                'message': f'Cached ({int(age/60)}m ago)',
            }

    if tickers is None:
        try:
            conn = get_db()
            watchlist = conn.execute("SELECT ticker FROM watchlist").fetchall()
            conn.close()
            watched = [row['ticker'] for row in watchlist]
            tickers = list(set(SCAN_UNIVERSE + watched))
        except Exception:
            tickers = list(SCAN_UNIVERSE)

    print(f"[Scanner] Fetching quotes for {len(tickers)} tickers...")
    start = time.time()

    quotes = _fetch_batch_quotes(tickers)
    elapsed = time.time() - start
    print(f"[Scanner] Got {len(quotes)} quotes in {elapsed:.1f}s")

    if not quotes:
        if cached and cached.get('results'):
            return {
                'status': 'rate_limited',
                'results': cached['results'],
                'message': 'Could not fetch live data. Showing last saved results.',
            }
        return {
            'status': 'rate_limited',
            'results': [],
            'message': 'Yahoo Finance is temporarily unavailable. Please wait a couple minutes and click Refresh.',
        }

    results = []
    for ticker in tickers:
        if ticker in quotes:
            r = _score_from_quote(ticker, quotes[ticker])
            if r:
                results.append(r)

    results.sort(key=lambda x: x['score'], reverse=True)
    print(f"[Scanner] Scored {len(results)} stocks")

    if results:
        _save_disk_cache(results)

    return {'status': 'ok', 'results': results, 'message': ''}


def get_todays_picks(limit=10):
    """Return the top actionable trade ideas right now."""
    scan_data = scan_stocks()
    all_results = scan_data.get('results', [])
    status = scan_data.get('status', 'ok')
    message = scan_data.get('message', '')

    buys = [r for r in all_results if r['score'] >= 60]
    sells = [r for r in all_results if r['score'] <= 35]
    buys.sort(key=lambda x: x['score'], reverse=True)
    sells.sort(key=lambda x: x['score'])

    today = date.today().strftime('%B %d, %Y')
    now = datetime.now().strftime('%I:%M %p')

    return {
        'generated_at': f'{today} at {now}',
        'total_scanned': len(all_results),
        'top_buys': buys[:limit],
        'top_sells': sells[:limit],
        'all_ranked': all_results,
        'status': status,
        'message': message,
    }


def get_trade_plan():
    """Generate a full trade plan with specific entry/exit levels."""
    picks = get_todays_picks(limit=5)
    plan = []

    for stock in picks['top_buys'][:5]:
        try:
            price = stock['price']
            stop_loss = round(price * 0.95, 2)
            target_1 = round(price * 1.05, 2)
            target_2 = round(price * 1.10, 2)
            risk = price - stop_loss
            reward = target_1 - price
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0
            entry_low = round(price * 0.99, 2)
            entry_high = round(price * 1.01, 2)

            plan.append({
                'ticker': stock['ticker'],
                'name': stock['name'],
                'sector': stock['sector'],
                'action': 'BUY',
                'score': stock['score'],
                'current_price': price,
                'entry_zone': f'${entry_low} \u2013 ${entry_high}',
                'stop_loss': stop_loss,
                'target_1': target_1,
                'target_2': target_2,
                'risk_reward': rr_ratio,
                'analyst_consensus': 'N/A',
                'reasons': stock['reasons'],
                'rsi': stock['rsi'],
                'day_change': stock['day_change'],
                'month_return': stock['month_return'],
                'volume_ratio': stock['volume_ratio'],
            })
        except Exception:
            continue

    for stock in picks['top_sells'][:3]:
        plan.append({
            'ticker': stock['ticker'],
            'name': stock['name'],
            'sector': stock['sector'],
            'action': 'SELL / AVOID',
            'score': stock['score'],
            'current_price': stock['price'],
            'entry_zone': '\u2014',
            'stop_loss': 0,
            'target_1': 0,
            'target_2': 0,
            'risk_reward': 0,
            'analyst_consensus': 'N/A',
            'reasons': stock['reasons'],
            'rsi': stock['rsi'],
            'day_change': stock['day_change'],
            'month_return': stock['month_return'],
            'volume_ratio': stock['volume_ratio'],
        })

    return {
        'generated_at': picks['generated_at'],
        'total_scanned': picks['total_scanned'],
        'plan': plan,
        'status': picks.get('status', 'ok'),
        'message': picks.get('message', ''),
    }
