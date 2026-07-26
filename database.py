# database.py — thread-safe SQLite with WAL mode
import sqlite3
import logging
import threading
import secrets
import string
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


def _gen_ref_code(length=8) -> str:
    """Generate a unique short referral code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


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

        CREATE TABLE IF NOT EXISTS users (
            telegram_id  INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            ref_code     TEXT UNIQUE,
            invited_by   INTEGER,
            total_invites INTEGER DEFAULT 0,
            joined_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            description      TEXT,
            image_path       TEXT,
            required_invites INTEGER DEFAULT 15,
            status           TEXT DEFAULT 'active',
            winner_id        INTEGER,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at         TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competition_entries (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER NOT NULL,
            user_id        INTEGER NOT NULL,
            invite_count   INTEGER DEFAULT 0,
            joined_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (user_id)        REFERENCES users(telegram_id),
            UNIQUE(competition_id, user_id)
        );
    """)

    # ── Safe migrations ──────────────────────────────────────
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


# ══════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════

def register_user(telegram_id: int, username: str, first_name: str,
                  invited_by: int = None) -> dict:
    """Register user if not exists, return user row."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM users WHERE telegram_id=?", (telegram_id,)
    ).fetchone()

    if existing:
        # Update username/first_name in case they changed
        conn.execute(
            "UPDATE users SET username=?, first_name=? WHERE telegram_id=?",
            (username, first_name, telegram_id)
        )
        conn.commit()
        return dict(existing)

    # Generate unique ref code
    while True:
        code = _gen_ref_code()
        exists = conn.execute("SELECT 1 FROM users WHERE ref_code=?", (code,)).fetchone()
        if not exists:
            break

    conn.execute(
        """INSERT INTO users (telegram_id, username, first_name, ref_code, invited_by)
           VALUES (?, ?, ?, ?, ?)""",
        (telegram_id, username, first_name, code, invited_by)
    )
    conn.commit()

    # Credit the inviter
    if invited_by:
        credit_invite(invited_by, telegram_id)

    return get_user(telegram_id)


def get_user(telegram_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_ref(ref_code: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE ref_code=?", (ref_code,)).fetchone()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY total_invites DESC, joined_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def credit_invite(inviter_id: int, new_user_id: int) -> None:
    """Credit the inviter for bringing in a new user."""
    conn = get_conn()
    conn.execute(
        "UPDATE users SET total_invites = total_invites + 1 WHERE telegram_id=?",
        (inviter_id,)
    )

    # Also update all active competition entries for this inviter
    active_comps = conn.execute(
        "SELECT id FROM competitions WHERE status='active'"
    ).fetchall()
    for comp in active_comps:
        conn.execute(
            """INSERT INTO competition_entries (competition_id, user_id, invite_count)
               VALUES (?, ?, 1)
               ON CONFLICT(competition_id, user_id)
               DO UPDATE SET invite_count = invite_count + 1""",
            (comp[0], inviter_id)
        )

    conn.commit()


# ══════════════════════════════════════════════
#  ACCOUNTS
# ══════════════════════════════════════════════

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
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [account_id]
    conn.execute(
        f"UPDATE accounts SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE id=?", values
    )
    conn.commit()


def delete_account(account_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()


# ══════════════════════════════════════════════
#  ORDERS
# ══════════════════════════════════════════════

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
    row  = conn.execute(
        """SELECT o.*, a.name as account_name, a.price, a.email, a.password,
                  a.features, a.image_path
           FROM orders o LEFT JOIN accounts a ON o.account_id=a.id
           WHERE o.id=?""",
        (order_id,)
    ).fetchone()
    return dict(row) if row else None


def get_all_orders() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, a.name as account_name
           FROM orders o LEFT JOIN accounts a ON o.account_id=a.id
           ORDER BY o.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_orders() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, a.name as account_name, a.price
           FROM orders o LEFT JOIN accounts a ON o.account_id=a.id
           WHERE o.status='pending'
           ORDER BY o.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def update_order(order_id: int, status: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()


# ══════════════════════════════════════════════
#  COMPETITIONS
# ══════════════════════════════════════════════

def create_competition(title: str, description: str = "", image_path: str = None,
                        required_invites: int = 15) -> int:
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        """INSERT INTO competitions (title, description, image_path, required_invites)
           VALUES (?, ?, ?, ?)""",
        (title, description, image_path, required_invites)
    )
    conn.commit()
    return c.lastrowid


def get_competition(comp_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM competitions WHERE id=?", (comp_id,)).fetchone()
    return dict(row) if row else None


def get_active_competitions() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM competitions WHERE status='active' ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_competitions() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM competitions ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def update_competition(comp_id: int, **kwargs) -> None:
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [comp_id]
    conn.execute(f"UPDATE competitions SET {fields} WHERE id=?", values)
    conn.commit()


def end_competition(comp_id: int, winner_id: int = None) -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE competitions SET status='ended', winner_id=?, ended_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (winner_id, comp_id)
    )
    conn.commit()


def delete_competition(comp_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM competition_entries WHERE competition_id=?", (comp_id,))
    conn.execute("DELETE FROM competitions WHERE id=?", (comp_id,))
    conn.commit()


def get_competition_entry(comp_id: int, user_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM competition_entries WHERE competition_id=? AND user_id=?",
        (comp_id, user_id)
    ).fetchone()
    return dict(row) if row else None


def get_competition_leaderboard(comp_id: int, limit: int = 10) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT ce.*, u.username, u.first_name
           FROM competition_entries ce
           LEFT JOIN users u ON ce.user_id = u.telegram_id
           WHERE ce.competition_id=?
           ORDER BY ce.invite_count DESC
           LIMIT ?""",
        (comp_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def join_competition(comp_id: int, user_id: int) -> None:
    """Make sure an entry exists for this user in this competition."""
    conn = get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO competition_entries (competition_id, user_id)
           VALUES (?, ?)""",
        (comp_id, user_id)
    )
    conn.commit()


def get_competition_participants_count(comp_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM competition_entries WHERE competition_id=?", (comp_id,)
    ).fetchone()
    return row[0] if row else 0


# ══════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════

def get_stats() -> dict:
    conn = get_conn()
    total     = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    available = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='available'").fetchone()[0]
    sold      = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'").fetchone()[0]
    revenue   = conn.execute(
        """SELECT COALESCE(SUM(a.price),0) FROM orders o
           JOIN accounts a ON o.account_id=a.id
           WHERE o.status='completed'"""
    ).fetchone()[0]
    pending   = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active_comps = conn.execute("SELECT COUNT(*) FROM competitions WHERE status='active'").fetchone()[0]

    return {
        "total_accounts": total,
        "available":      available,
        "sold":           sold,
        "revenue":        round(float(revenue), 2),
        "pending_orders": pending,
        "total_orders":   total_orders,
        "total_users":    total_users,
        "active_competitions": active_comps,
    }
