import yfinance as yf
import pandas as pd
import requests as _requests
from datetime import datetime, timedelta
from functools import lru_cache
import time
import json

_cache = {}
_cache_ttl = {}
CACHE_DURATION = 300  # 5 minutes

_yahoo_session = None
_yahoo_crumb = ''
_yahoo_session_time = 0


def _get_cached(key, fetcher, ttl=CACHE_DURATION):
    now = time.time()
    if key in _cache and now - _cache_ttl.get(key, 0) < ttl:
        return _cache[key]
    result = fetcher()
    if result is not None:
        _cache[key] = result
        _cache_ttl[key] = now
    return result


def _ensure_yahoo_session():
    """Maintain an authenticated Yahoo Finance session with crumb token."""
    global _yahoo_session, _yahoo_crumb, _yahoo_session_time
    if _yahoo_session and (time.time() - _yahoo_session_time) < 1800:
        return _yahoo_session, _yahoo_crumb
    try:
        session = _requests.Session()
        session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        session.get('https://fc.yahoo.com/', allow_redirects=True, timeout=10)
        r = session.get('https://query2.finance.yahoo.com/v1/test/getcrumb', timeout=10)
        crumb = r.text.strip() if r.status_code == 200 else ''
        if crumb:
            _yahoo_session = session
            _yahoo_crumb = crumb
            _yahoo_session_time = time.time()
            return session, crumb
    except Exception:
        pass
    return _yahoo_session, _yahoo_crumb


def _fetch_quote_direct(ticker):
    """Fetch a single stock's quote via the authenticated Yahoo Finance API (bypasses yfinance rate limits)."""
    session, crumb = _ensure_yahoo_session()
    if not session or not crumb:
        return None
    try:
        resp = session.get(
            'https://query2.finance.yahoo.com/v7/finance/quote',
            params={'symbols': ticker.upper(), 'crumb': crumb},
            timeout=10,
        )
        if resp.status_code == 200:
            quotes = resp.json().get('quoteResponse', {}).get('result', [])
            if quotes:
                return quotes[0]
    except Exception:
        pass
    return None


def _quote_to_stock_info(q, ticker):
    """Convert a Yahoo Finance quote dict into the standard stock_info format."""
    price = q.get('regularMarketPrice') or q.get('currentPrice', 0)
    prev_close = q.get('regularMarketPreviousClose') or q.get('previousClose', 0)
    return {
        'symbol': q.get('symbol', ticker.upper()),
        'name': q.get('longName') or q.get('shortName', ticker.upper()),
        'price': price,
        'previous_close': prev_close,
        'open': q.get('regularMarketOpen', 0),
        'day_high': q.get('regularMarketDayHigh', 0),
        'day_low': q.get('regularMarketDayLow', 0),
        'volume': q.get('regularMarketVolume', 0),
        'avg_volume': q.get('averageDailyVolume3Month') or q.get('averageDailyVolume10Day', 0),
        'market_cap': q.get('marketCap', 0),
        'pe_ratio': q.get('trailingPE', 0),
        'forward_pe': q.get('forwardPE', 0),
        'eps': q.get('epsTrailingTwelveMonths', 0),
        'dividend_yield': q.get('trailingAnnualDividendYield', 0),
        'fifty_two_week_high': q.get('fiftyTwoWeekHigh', 0),
        'fifty_two_week_low': q.get('fiftyTwoWeekLow', 0),
        'fifty_day_avg': q.get('fiftyDayAverage', 0),
        'two_hundred_day_avg': q.get('twoHundredDayAverage', 0),
        'beta': q.get('beta', 0),
        'sector': q.get('sector', 'N/A'),
        'industry': q.get('industry', 'N/A'),
        'description': '',
        'website': '',
        'exchange': q.get('exchange', ''),
        'currency': q.get('currency', 'USD'),
        'change': 0,
        'change_percent': 0,
    }


def get_stock_info(ticker):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if not info or 'symbol' not in info:
                raise ValueError("No data from yfinance")

            return {
                'symbol': info.get('symbol', ticker.upper()),
                'name': info.get('longName') or info.get('shortName', ticker.upper()),
                'price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                'previous_close': info.get('previousClose') or info.get('regularMarketPreviousClose', 0),
                'open': info.get('open') or info.get('regularMarketOpen', 0),
                'day_high': info.get('dayHigh') or info.get('regularMarketDayHigh', 0),
                'day_low': info.get('dayLow') or info.get('regularMarketDayLow', 0),
                'volume': info.get('volume') or info.get('regularMarketVolume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'eps': info.get('trailingEps', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'fifty_day_avg': info.get('fiftyDayAverage', 0),
                'two_hundred_day_avg': info.get('twoHundredDayAverage', 0),
                'beta': info.get('beta', 0),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website', ''),
                'exchange': info.get('exchange', ''),
                'currency': info.get('currency', 'USD'),
                'change': 0,
                'change_percent': 0,
            }
        except Exception as e:
            print(f"yfinance failed for {ticker}: {e}, trying direct API...")
            q = _fetch_quote_direct(ticker)
            if q:
                return _quote_to_stock_info(q, ticker)
            return None

    result = _get_cached(f"info_{ticker}", fetch)
    if result and result.get('previous_close'):
        result['change'] = round(result['price'] - result['previous_close'], 2)
        pct = (result['change'] / result['previous_close'] * 100) if result['previous_close'] else 0
        result['change_percent'] = round(pct, 2)
    return result


def _fetch_chart_direct(ticker, period='1y', interval='1d'):
    """Fetch chart data via authenticated Yahoo Finance API when yfinance is rate-limited."""
    range_map = {'5d': '5d', '1mo': '1mo', '3mo': '3mo', '6mo': '6mo', '1y': '1y', '2y': '2y', '5y': '5y', 'max': 'max'}
    yf_range = range_map.get(period, '1y')
    session, crumb = _ensure_yahoo_session()
    if not session or not crumb:
        return []
    try:
        resp = session.get(
            f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker.upper()}',
            params={'range': yf_range, 'interval': interval, 'crumb': crumb},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        chart = resp.json().get('chart', {}).get('result', [])
        if not chart:
            return []
        result = chart[0]
        timestamps = result.get('timestamp', [])
        ohlcv = result.get('indicators', {}).get('quote', [{}])[0]
        opens = ohlcv.get('open', [])
        highs = ohlcv.get('high', [])
        lows = ohlcv.get('low', [])
        closes = ohlcv.get('close', [])
        volumes = ohlcv.get('volume', [])

        data = []
        for i, ts in enumerate(timestamps):
            if closes[i] is None:
                continue
            dt = datetime.fromtimestamp(ts)
            fmt = '%Y-%m-%d' if interval in ['1d', '1wk', '1mo'] else '%Y-%m-%d %H:%M'
            data.append({
                'date': dt.strftime(fmt),
                'open': round(opens[i] or 0, 2),
                'high': round(highs[i] or 0, 2),
                'low': round(lows[i] or 0, 2),
                'close': round(closes[i] or 0, 2),
                'volume': int(volumes[i] or 0),
            })
        return data
    except Exception as e:
        print(f"Direct chart API failed for {ticker}: {e}")
        return []


def get_stock_history(ticker, period='1y', interval='1d'):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            if hist.empty:
                raise ValueError("Empty history")

            data = []
            for date, row in hist.iterrows():
                data.append({
                    'date': date.strftime('%Y-%m-%d') if interval in ['1d', '1wk', '1mo'] else date.strftime('%Y-%m-%d %H:%M'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume']),
                })
            return data
        except Exception as e:
            print(f"yfinance history failed for {ticker}: {e}, trying direct API...")
            return _fetch_chart_direct(ticker, period, interval)

    return _get_cached(f"history_{ticker}_{period}_{interval}", fetch)


def get_recommendations(ticker):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            rec = stock.recommendations
            if rec is None or rec.empty:
                return []

            results = []
            for _, row in rec.tail(20).iterrows():
                results.append({
                    'firm': row.get('Firm', 'Unknown'),
                    'grade': row.get('To Grade', row.get('toGrade', 'N/A')),
                    'action': row.get('Action', row.get('action', 'N/A')),
                })
            return list(reversed(results))
        except Exception as e:
            print(f"Error fetching recommendations for {ticker}: {e}")
            return []

    return _get_cached(f"rec_{ticker}", fetch, ttl=900)


def get_recommendation_summary(ticker):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            trend = stock.recommendations_summary
            if trend is None or trend.empty:
                return None

            latest = trend.iloc[0]
            return {
                'strong_buy': int(latest.get('strongBuy', 0)),
                'buy': int(latest.get('buy', 0)),
                'hold': int(latest.get('hold', 0)),
                'sell': int(latest.get('sell', 0)),
                'strong_sell': int(latest.get('strongSell', 0)),
            }
        except Exception:
            return None

    return _get_cached(f"rec_summary_{ticker}", fetch, ttl=900)


def get_financials(ticker):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            income = stock.income_stmt
            balance = stock.balance_sheet

            result = {'income': [], 'balance': []}

            if income is not None and not income.empty:
                for col in income.columns[:4]:
                    period_data = {'period': col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}
                    for idx in income.index:
                        val = income.loc[idx, col]
                        period_data[str(idx)] = float(val) if pd.notna(val) else None
                    result['income'].append(period_data)

            if balance is not None and not balance.empty:
                for col in balance.columns[:4]:
                    period_data = {'period': col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}
                    for idx in balance.index:
                        val = balance.loc[idx, col]
                        period_data[str(idx)] = float(val) if pd.notna(val) else None
                    result['balance'].append(period_data)

            return result
        except Exception as e:
            print(f"Error fetching financials for {ticker}: {e}")
            return {'income': [], 'balance': []}

    return _get_cached(f"fin_{ticker}", fetch, ttl=3600)


def search_stocks(query):
    try:
        query = query.upper().strip()
        popular = {
            'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corporation', 'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.', 'META': 'Meta Platforms Inc.', 'TSLA': 'Tesla Inc.',
            'NVDA': 'NVIDIA Corporation', 'JPM': 'JPMorgan Chase & Co.', 'V': 'Visa Inc.',
            'JNJ': 'Johnson & Johnson', 'WMT': 'Walmart Inc.', 'PG': 'Procter & Gamble Co.',
            'MA': 'Mastercard Inc.', 'UNH': 'UnitedHealth Group Inc.', 'HD': 'The Home Depot Inc.',
            'DIS': 'The Walt Disney Company', 'NFLX': 'Netflix Inc.', 'ADBE': 'Adobe Inc.',
            'CRM': 'Salesforce Inc.', 'PYPL': 'PayPal Holdings Inc.', 'INTC': 'Intel Corporation',
            'AMD': 'Advanced Micro Devices Inc.', 'BA': 'The Boeing Company',
            'NKE': 'NIKE Inc.', 'COST': 'Costco Wholesale Corp.', 'PEP': 'PepsiCo Inc.',
            'KO': 'The Coca-Cola Company', 'ABBV': 'AbbVie Inc.', 'MRK': 'Merck & Co. Inc.',
            'XOM': 'Exxon Mobil Corporation', 'CVX': 'Chevron Corporation',
            'LLY': 'Eli Lilly and Company', 'AVGO': 'Broadcom Inc.', 'ORCL': 'Oracle Corporation',
            'ACN': 'Accenture plc', 'TXN': 'Texas Instruments Inc.',
            'QCOM': 'QUALCOMM Inc.', 'NOW': 'ServiceNow Inc.', 'AMAT': 'Applied Materials Inc.',
            'INTU': 'Intuit Inc.', 'ISRG': 'Intuitive Surgical Inc.',
            'BKNG': 'Booking Holdings Inc.', 'SPOT': 'Spotify Technology S.A.',
            'SQ': 'Block Inc.', 'SHOP': 'Shopify Inc.', 'SNAP': 'Snap Inc.',
            'UBER': 'Uber Technologies Inc.', 'ABNB': 'Airbnb Inc.', 'PLTR': 'Palantir Technologies Inc.',
            'COIN': 'Coinbase Global Inc.', 'SOFI': 'SoFi Technologies Inc.',
            'SPY': 'SPDR S&P 500 ETF', 'QQQ': 'Invesco QQQ Trust', 'IWM': 'iShares Russell 2000 ETF',
            'DIA': 'SPDR Dow Jones Industrial Average ETF', 'VTI': 'Vanguard Total Stock Market ETF',
        }

        results = []
        for sym, name in popular.items():
            if query in sym or query.lower() in name.lower():
                results.append({'symbol': sym, 'name': name})

        if not results:
            try:
                stock = yf.Ticker(query)
                info = stock.info
                if info and 'symbol' in info:
                    results.append({
                        'symbol': info.get('symbol', query),
                        'name': info.get('longName') or info.get('shortName', query)
                    })
            except Exception:
                pass

        return results[:10]
    except Exception as e:
        print(f"Error searching stocks: {e}")
        return []


def get_options_expirations(ticker):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            return list(expirations) if expirations else []
        except Exception as e:
            print(f"Error fetching options expirations for {ticker}: {e}")
            return []

    result = _get_cached(f"opt_exp_{ticker}", fetch, ttl=600)
    if not result:
        _cache.pop(f"opt_exp_{ticker}", None)
    return result


def get_options_chain(ticker, expiration):
    def fetch():
        try:
            stock = yf.Ticker(ticker)
            chain = stock.option_chain(expiration)
            info = get_stock_info(ticker)
            underlying_price = info['price'] if info else 0

            def parse_side(df, option_type):
                rows = []
                for _, row in df.iterrows():
                    strike = float(row.get('strike', 0))
                    last = float(row.get('lastPrice', 0))
                    bid = float(row.get('bid', 0))
                    ask = float(row.get('ask', 0))
                    volume = int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0
                    oi = int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0
                    iv = float(row.get('impliedVolatility', 0))
                    change = float(row.get('change', 0)) if pd.notna(row.get('change')) else 0
                    pct_change = float(row.get('percentChange', 0)) if pd.notna(row.get('percentChange')) else 0
                    contract = str(row.get('contractSymbol', ''))

                    itm = (strike < underlying_price) if option_type == 'call' else (strike > underlying_price)

                    rows.append({
                        'contract': contract,
                        'strike': round(strike, 2),
                        'last': round(last, 2),
                        'bid': round(bid, 2),
                        'ask': round(ask, 2),
                        'change': round(change, 2),
                        'pct_change': round(pct_change, 2),
                        'volume': volume,
                        'open_interest': oi,
                        'iv': round(iv * 100, 1),
                        'itm': itm,
                    })
                return rows

            calls = parse_side(chain.calls, 'call') if chain.calls is not None and not chain.calls.empty else []
            puts = parse_side(chain.puts, 'put') if chain.puts is not None and not chain.puts.empty else []

            return {
                'ticker': ticker.upper(),
                'expiration': expiration,
                'underlying_price': underlying_price,
                'calls': calls,
                'puts': puts,
            }
        except Exception as e:
            print(f"Error fetching options chain for {ticker} {expiration}: {e}")
            return None

    result = _get_cached(f"opt_chain_{ticker}_{expiration}", fetch, ttl=120)
    if not result:
        _cache.pop(f"opt_chain_{ticker}_{expiration}", None)
    return result


def get_market_overview():
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones',
        '^IXIC': 'NASDAQ',
        '^RUT': 'Russell 2000',
        '^VIX': 'VIX',
    }

    def fetch():
        symbols_str = ','.join(indices.keys())
        session, crumb = _ensure_yahoo_session()
        results = []

        if session and crumb:
            try:
                resp = session.get(
                    'https://query2.finance.yahoo.com/v7/finance/quote',
                    params={'symbols': symbols_str, 'crumb': crumb},
                    timeout=10,
                )
                if resp.status_code == 200:
                    quotes = resp.json().get('quoteResponse', {}).get('result', [])
                    for q in quotes:
                        sym = q.get('symbol', '')
                        name = indices.get(sym, sym)
                        price = q.get('regularMarketPrice', 0)
                        prev = q.get('regularMarketPreviousClose', 0)
                        change = round(price - prev, 2) if prev else 0
                        change_pct = round((change / prev) * 100, 2) if prev else 0
                        results.append({
                            'symbol': sym, 'name': name,
                            'price': round(price, 2), 'change': change, 'change_percent': change_pct,
                        })
                    if results:
                        return results
            except Exception:
                pass

        for symbol, name in indices.items():
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                price = info.get('regularMarketPrice') or info.get('previousClose', 0)
                prev = info.get('regularMarketPreviousClose') or info.get('previousClose', 0)
                change = round(price - prev, 2) if prev else 0
                change_pct = round((change / prev) * 100, 2) if prev else 0
                results.append({
                    'symbol': symbol, 'name': name,
                    'price': round(price, 2), 'change': change, 'change_percent': change_pct,
                })
            except Exception:
                results.append({
                    'symbol': symbol, 'name': name,
                    'price': 0, 'change': 0, 'change_percent': 0,
                })
        return results

    return _get_cached('market_overview', fetch, ttl=120)
