import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'elephante.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
            quantity REAL NOT NULL CHECK(quantity > 0),
            price REAL NOT NULL CHECK(price > 0),
            total REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            quantity REAL NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            total_invested REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            cash_balance REAL NOT NULL DEFAULT 100000.00,
            initial_balance REAL NOT NULL DEFAULT 100000.00
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            condition TEXT NOT NULL,
            target_price REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS options_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            option_type TEXT NOT NULL CHECK(option_type IN ('CALL', 'PUT')),
            strike REAL NOT NULL CHECK(strike > 0),
            expiration TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
            contracts INTEGER NOT NULL CHECK(contracts > 0),
            premium REAL NOT NULL CHECK(premium >= 0),
            total REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS options_portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            option_type TEXT NOT NULL,
            strike REAL NOT NULL,
            expiration TEXT NOT NULL,
            contracts INTEGER NOT NULL DEFAULT 0,
            avg_premium REAL NOT NULL DEFAULT 0,
            total_invested REAL NOT NULL DEFAULT 0,
            UNIQUE(ticker, option_type, strike, expiration)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            order_type TEXT NOT NULL CHECK(order_type IN ('STOP_LOSS', 'TAKE_PROFIT', 'TRAILING_STOP')),
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
            quantity REAL NOT NULL CHECK(quantity > 0),
            trigger_price REAL,
            trail_percent REAL,
            trail_high REAL,
            status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'TRIGGERED', 'CANCELLED')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_at TIMESTAMP,
            notes TEXT DEFAULT ''
        );
    ''')

    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account (id, cash_balance, initial_balance) VALUES (1, 100000.00, 100000.00)")

    conn.commit()
    conn.close()


def reset_account(initial_balance=100000.0):
    conn = get_db()
    conn.execute("DELETE FROM paper_trades")
    conn.execute("DELETE FROM portfolio")
    conn.execute("DELETE FROM options_trades")
    conn.execute("DELETE FROM options_portfolio")
    conn.execute("DELETE FROM orders")
    conn.execute("UPDATE account SET cash_balance = ?, initial_balance = ? WHERE id = 1",
                 (initial_balance, initial_balance))
    conn.commit()
    conn.close()
