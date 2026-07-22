# database.py — thread-safe SQLite with WAL mode
import sqlite3
import logging
import threading
from typing import Optional

DB_NAME = "shop.db"
logger  = logging.getLogger(__name__)

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    c    = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            description   TEXT,
            price         REAL    NOT NULL DEFAULT 0,
            creation_year INTEGER,
            category      TEXT    DEFAULT 'twitter',
            image_path    TEXT,
            email         TEXT,
            password      TEXT,
            followers     INTEGER DEFAULT 0,
            tweets_count  INTEGER DEFAULT 0,
            features      TEXT,
            status        TEXT    DEFAULT 'available',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id     INTEGER,
            buyer_id       INTEGER,
            buyer_username TEXT,
            status         TEXT DEFAULT 'pending',
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS admins (
            telegram_id INTEGER PRIMARY KEY,
            username    TEXT,
            is_active   BOOLEAN DEFAULT 1
        );
    """)

    # Safe migration: add new columns if missing
    existing = {row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()}
    new_cols = {
        "email":        "TEXT",
        "password":     "TEXT",
        "followers":    "INTEGER DEFAULT 0",
        "tweets_count": "INTEGER DEFAULT 0",
        "features":     "TEXT",
    }
    for col, typedef in new_cols.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE accounts ADD COLUMN {col} {typedef}")
            logger.info(f"Migrated: added column {col}")

    import os
    admin_id       = int(os.environ.get("ADMIN_ID", "8989271393"))
    admin_username = os.environ.get("ADMIN_USERNAME", "l825h")
    c.execute(
        "INSERT OR IGNORE INTO admins (telegram_id, username) VALUES (?, ?)",
        (admin_id, admin_username)
    )
    conn.commit()
    logger.info("✅ Database initialised.")


# ── Accounts ───────────────────────────────────────────────

def add_account(name, description="", price=0, creation_year=None,
                category="twitter", image_path=None,
                email="", password="", followers=0,
                tweets_count=0, features="") -> int:
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        """INSERT INTO accounts
           (name, description, price, creation_year, category, image_path,
            email, password, followers, tweets_count, features)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, description, float(price), creation_year, category, image_path,
         email, password, int(followers or 0), int(tweets_count or 0), features)
    )
    conn.commit()
    return c.lastrowid


def get_all_accounts(status="available") -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM accounts WHERE status=? ORDER BY created_at DESC", (status,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_accounts_admin() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM accounts ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_account(account_id: int) -> Optional[dict]:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return dict(row) if row else None


def update_account(account_id: int, **kwargs) -> None:
    allowed = {
        "name", "description", "price", "creation_year", "category",
        "image_path", "status", "email", "password", "followers",
        "tweets_count", "features"
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    conn       = get_conn()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values     = [*updates.values(), account_id]
    conn.execute(
        f"UPDATE accounts SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        values
    )
    conn.commit()


def delete_account(account_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()


# ── Orders ─────────────────────────────────────────────────

def create_order(account_id: int, buyer_id: int, buyer_username: str) -> int:
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        "INSERT INTO orders (account_id, buyer_id, buyer_username) VALUES (?, ?, ?)",
        (account_id, buyer_id, buyer_username)
    )
    conn.commit()
    return c.lastrowid


def get_order(order_id: int) -> Optional[dict]:
    conn = get_conn()
    row  = conn.execute("""
        SELECT o.*, a.name AS account_name, a.price AS account_price,
               a.email AS account_email, a.password AS account_password,
               a.features AS account_features
        FROM orders o
        LEFT JOIN accounts a ON o.account_id = a.id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    return dict(row) if row else None


def get_all_orders() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.*, a.name AS account_name, a.price AS account_price
        FROM   orders   o
        LEFT JOIN accounts a ON o.account_id = a.id
        ORDER BY o.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_pending_orders() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT o.*, a.name AS account_name, a.price AS account_price
        FROM   orders   o
        LEFT JOIN accounts a ON o.account_id = a.id
        WHERE o.status = 'pending'
        ORDER BY o.created_at DESC
    """).fetchall()
    return [dict(r) for r in rows]


def update_order(order_id: int, status: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()


# ── Stats ──────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_conn()
    def scalar(sql, *args):
        return conn.execute(sql, args).fetchone()[0]

    return {
        "total":        scalar("SELECT COUNT(*) FROM accounts"),
        "available":    scalar("SELECT COUNT(*) FROM accounts WHERE status='available'"),
        "sold":         scalar("SELECT COUNT(*) FROM accounts WHERE status='sold'"),
        "reserved":     scalar("SELECT COUNT(*) FROM accounts WHERE status='reserved'"),
        "revenue":      scalar(
            "SELECT COALESCE(SUM(a.price),0) FROM orders o "
            "JOIN accounts a ON o.account_id=a.id "
            "WHERE o.status IN ('paid','completed')"
        ),
        "total_orders": scalar("SELECT COUNT(*) FROM orders"),
        "pending_orders": scalar("SELECT COUNT(*) FROM orders WHERE status='pending'"),
    }


# ── Initialise on import ───────────────────────────────────
init_db()
