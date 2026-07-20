# database.py
import sqlite3
import json
import logging
from datetime import datetime

DB_NAME = "shop.db"
logger = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            creation_year INTEGER,
            category TEXT DEFAULT 'twitter',
            image_path TEXT,
            status TEXT DEFAULT 'available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            buyer_id INTEGER,
            buyer_username TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Insert default admin
    c.execute('''
        INSERT OR IGNORE INTO admins (telegram_id, username) VALUES (?, ?)
    ''', (8989271393, 'l825h'))

    conn.commit()
    conn.close()
    logger.info("Database initialised.")


# ── Accounts ──────────────────────────────────────────────

def add_account(name, description, price, creation_year=None,
                category='twitter', image_path=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO accounts (name, description, price, creation_year, category, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, description, price, creation_year, category, image_path))
    conn.commit()
    account_id = c.lastrowid
    conn.close()
    return account_id


def get_all_accounts(status='available'):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM accounts WHERE status=? ORDER BY created_at DESC',
        (status,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_accounts_admin():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM accounts ORDER BY created_at DESC')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_account(account_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM accounts WHERE id=?', (account_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_account(account_id, **kwargs):
    allowed = ['name', 'description', 'price', 'creation_year',
               'category', 'image_path', 'status']
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    conn = get_conn()
    c = conn.cursor()
    set_clause = ', '.join([f"{k}=?" for k in updates])
    values = list(updates.values()) + [account_id]
    c.execute(
        f'UPDATE accounts SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=?',
        values
    )
    conn.commit()
    conn.close()


def delete_account(account_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    conn.commit()
    conn.close()


# ── Orders ────────────────────────────────────────────────

def create_order(account_id, buyer_id, buyer_username):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (account_id, buyer_id, buyer_username)
        VALUES (?, ?, ?)
    ''', (account_id, buyer_id, buyer_username))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id


def get_all_orders():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT o.*, a.name as account_name, a.price as account_price
        FROM orders o
        LEFT JOIN accounts a ON o.account_id = a.id
        ORDER BY o.created_at DESC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_order(order_id, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE orders SET status=? WHERE id=?', (status, order_id))
    conn.commit()
    conn.close()


# ── Stats ─────────────────────────────────────────────────

def get_stats():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM accounts")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")
    available = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'")
    sold = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM accounts WHERE status='reserved'")
    reserved = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(a.price),0) FROM orders o JOIN accounts a ON o.account_id=a.id WHERE o.status IN ('paid','completed')")
    revenue = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    conn.close()
    return {
        'total': total,
        'available': available,
        'sold': sold,
        'reserved': reserved,
        'revenue': revenue,
        'total_orders': total_orders
    }


# Initialise on import
init_db()
