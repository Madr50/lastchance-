# database.py
import sqlite3
from datetime import datetime
import json

DB_NAME = "shop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول الحسابات
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT DEFAULT 'twitter',
            image_path TEXT,
            status TEXT DEFAULT 'available',  -- available, sold, reserved
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'  -- JSON لبيانات إضافية
        )
    ''')
    
    # جدول الطلبات
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            buyer_id INTEGER,
            buyer_username TEXT,
            status TEXT DEFAULT 'pending',  -- pending, paid, completed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_account(name, description, price, category="twitter", image_path=None, metadata=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO accounts (name, description, price, category, image_path, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, description, price, category, image_path, json.dumps(metadata or {})))
    conn.commit()
    account_id = c.lastrowid
    conn.close()
    return account_id

def get_all_accounts(status="available"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM accounts WHERE status=? ORDER BY created_at DESC', (status,))
    accounts = c.fetchall()
    conn.close()
    return accounts

def get_account(account_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM accounts WHERE id=?', (account_id,))
    account = c.fetchone()
    conn.close()
    return account

def update_account(account_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    allowed = ['name', 'description', 'price', 'image_path', 'status', 'metadata']
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    
    if updates:
        set_clause = ', '.join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [account_id]
        c.execute(f'UPDATE accounts SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=?', values)
        conn.commit()
    
    conn.close()

def delete_account(account_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    conn.commit()
    conn.close()

def create_order(account_id, buyer_id, buyer_username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (account_id, buyer_id, buyer_username)
        VALUES (?, ?, ?)
    ''', (account_id, buyer_id, buyer_username))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id

# تهيئة القاعدة
init_db()
