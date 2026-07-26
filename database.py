# database.py — Production-grade marketplace database with full schema
import sqlite3
import logging
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

DB_NAME = "shop.db"
logger = logging.getLogger(__name__)
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Get thread-local SQLite connection with WAL mode."""
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    """Initialize all marketplace tables with proper schema and indexes."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        -- ============================================================
        -- USERS (Sellers & Buyers)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id         INTEGER UNIQUE NOT NULL,
            username            TEXT,
            first_name          TEXT,
            last_name           TEXT,
            avatar_url          TEXT,
            cover_url           TEXT,
            bio                 TEXT,
            
            -- Ratings & Reviews
            rating              REAL DEFAULT 5.0,
            review_count        INTEGER DEFAULT 0,
            positive_reviews    INTEGER DEFAULT 0,
            negative_reviews    INTEGER DEFAULT 0,
            
            -- Statistics
            followers           INTEGER DEFAULT 0,
            following           INTEGER DEFAULT 0,
            total_listings      INTEGER DEFAULT 0,
            completed_sales     INTEGER DEFAULT 0,
            completed_purchases INTEGER DEFAULT 0,
            
            -- Verification
            is_verified         BOOLEAN DEFAULT 0,
            verification_date   TIMESTAMP,
            
            -- Account Status
            is_banned           BOOLEAN DEFAULT 0,
            ban_reason          TEXT,
            ban_date            TIMESTAMP,
            
            -- Preferences
            language            TEXT DEFAULT 'en',
            currency            TEXT DEFAULT 'USD',
            notification_enabled BOOLEAN DEFAULT 1,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_is_banned ON users(is_banned);

        -- ============================================================
        -- LISTINGS (Products for Sale)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS listings (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id           INTEGER NOT NULL,
            title               TEXT NOT NULL,
            description         TEXT,
            
            -- Classification
            category_id         INTEGER,
            platform_id         INTEGER,
            
            -- Media
            main_image_url      TEXT,
            image_urls          TEXT,  -- JSON array
            video_url           TEXT,
            
            -- Details
            price               REAL NOT NULL,
            currency            TEXT DEFAULT 'USD',
            is_negotiable       BOOLEAN DEFAULT 1,
            
            -- Location & Language
            country             TEXT,
            language            TEXT,
            
            -- Metadata
            tags                TEXT,  -- JSON array
            extra_details       TEXT,  -- JSON object
            
            -- Status
            status              TEXT DEFAULT 'active',  -- active, sold, reserved, hidden
            is_featured         BOOLEAN DEFAULT 0,
            featured_until      TIMESTAMP,
            view_count          INTEGER DEFAULT 0,
            like_count          INTEGER DEFAULT 0,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_listings_seller_id ON listings(seller_id);
        CREATE INDEX IF NOT EXISTS idx_listings_category_id ON listings(category_id);
        CREATE INDEX IF NOT EXISTS idx_listings_platform_id ON listings(platform_id);
        CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
        CREATE INDEX IF NOT EXISTS idx_listings_is_featured ON listings(is_featured);
        CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
        CREATE INDEX IF NOT EXISTS idx_listings_country ON listings(country);

        -- ============================================================
        -- CATEGORIES
        -- ============================================================
        CREATE TABLE IF NOT EXISTS categories (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL UNIQUE,
            slug                TEXT NOT NULL UNIQUE,
            description         TEXT,
            icon                TEXT,  -- Emoji or icon name
            banner_url          TEXT,
            color               TEXT,  -- Hex color
            accent_color        TEXT,
            illustration_url    TEXT,
            
            -- Visual Design
            gradient_start      TEXT,
            gradient_end        TEXT,
            
            -- Metadata
            display_order       INTEGER DEFAULT 0,
            is_active           BOOLEAN DEFAULT 1,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
        CREATE INDEX IF NOT EXISTS idx_categories_is_active ON categories(is_active);

        -- ============================================================
        -- PLATFORMS (Specific to games/services)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS platforms (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL UNIQUE,
            slug                TEXT NOT NULL UNIQUE,
            category_id         INTEGER,
            description         TEXT,
            icon                TEXT,
            banner_url          TEXT,
            color               TEXT,
            accent_color        TEXT,
            illustration_url    TEXT,
            
            -- Visual Design
            gradient_start      TEXT,
            gradient_end        TEXT,
            
            -- Metadata
            display_order       INTEGER DEFAULT 0,
            is_active           BOOLEAN DEFAULT 1,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_platforms_slug ON platforms(slug);
        CREATE INDEX IF NOT EXISTS idx_platforms_category_id ON platforms(category_id);
        CREATE INDEX IF NOT EXISTS idx_platforms_is_active ON platforms(is_active);

        -- ============================================================
        -- ORDERS & TRANSACTIONS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS orders (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id          INTEGER NOT NULL,
            buyer_id            INTEGER NOT NULL,
            seller_id           INTEGER NOT NULL,
            
            -- Order Status
            status              TEXT DEFAULT 'pending',  -- pending, paid, delivered, completed, disputed, cancelled
            
            -- Payment
            payment_method      TEXT,  -- stars, usdt, bank_transfer
            amount              REAL NOT NULL,
            currency            TEXT DEFAULT 'USD',
            payment_id          TEXT,  -- Transaction ID
            
            -- Commission
            commission_amount   REAL DEFAULT 0,
            commission_percent  REAL DEFAULT 0,
            net_amount          REAL,  -- Amount seller receives
            
            -- Dates
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at             TIMESTAMP,
            delivered_at        TIMESTAMP,
            completed_at        TIMESTAMP,
            
            FOREIGN KEY (listing_id) REFERENCES listings(id),
            FOREIGN KEY (buyer_id) REFERENCES users(id),
            FOREIGN KEY (seller_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_buyer_id ON orders(buyer_id);
        CREATE INDEX IF NOT EXISTS idx_orders_seller_id ON orders(seller_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_payment_method ON orders(payment_method);

        -- ============================================================
        -- PRIVATE CHAT & MESSAGES
        -- ============================================================
        CREATE TABLE IF NOT EXISTS chats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_1_id    INTEGER NOT NULL,
            participant_2_id    INTEGER NOT NULL,
            listing_id          INTEGER,  -- Link to listing (optional)
            order_id            INTEGER,  -- Link to order (optional)
            
            -- Chat Status
            is_active           BOOLEAN DEFAULT 1,
            participant_1_muted BOOLEAN DEFAULT 0,
            participant_2_muted BOOLEAN DEFAULT 0,
            participant_1_blocked_by_2 BOOLEAN DEFAULT 0,
            participant_2_blocked_by_1 BOOLEAN DEFAULT 0,
            
            -- Message Counts
            unread_count_1      INTEGER DEFAULT 0,
            unread_count_2      INTEGER DEFAULT 0,
            
            -- Metadata
            last_message_id     INTEGER,
            last_message_at     TIMESTAMP,
            pinned_message_id   INTEGER,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (participant_1_id) REFERENCES users(id),
            FOREIGN KEY (participant_2_id) REFERENCES users(id),
            FOREIGN KEY (listing_id) REFERENCES listings(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE INDEX IF NOT EXISTS idx_chats_participant_1 ON chats(participant_1_id);
        CREATE INDEX IF NOT EXISTS idx_chats_participant_2 ON chats(participant_2_id);
        CREATE INDEX IF NOT EXISTS idx_chats_is_active ON chats(is_active);

        CREATE TABLE IF NOT EXISTS messages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id             INTEGER NOT NULL,
            sender_id           INTEGER NOT NULL,
            receiver_id         INTEGER NOT NULL,
            
            -- Message Content
            message_type        TEXT DEFAULT 'text',  -- text, image, file, voice, reply
            content             TEXT NOT NULL,
            
            -- Media/Attachments
            media_url           TEXT,
            media_type          TEXT,  -- image, file, voice, etc.
            
            -- Reply & Context
            reply_to_id         INTEGER,  -- Message ID this replies to
            
            -- Status
            is_read             BOOLEAN DEFAULT 0,
            is_delivered        BOOLEAN DEFAULT 0,
            is_deleted          BOOLEAN DEFAULT 0,
            
            -- Metadata
            is_pinned           BOOLEAN DEFAULT 0,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at             TIMESTAMP,
            
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id),
            FOREIGN KEY (reply_to_id) REFERENCES messages(id)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
        CREATE INDEX IF NOT EXISTS idx_messages_is_read ON messages(is_read);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

        -- ============================================================
        -- REVIEWS & RATINGS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS reviews (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id            INTEGER NOT NULL,
            reviewer_id         INTEGER NOT NULL,
            reviewee_id         INTEGER NOT NULL,
            
            rating              REAL NOT NULL,  -- 1-5
            title               TEXT,
            comment             TEXT,
            
            -- Reviewer Role
            reviewer_role       TEXT,  -- seller, buyer
            
            -- Status
            is_verified         BOOLEAN DEFAULT 0,  -- Verified purchase review
            is_helpful          INTEGER DEFAULT 0,  -- Helpful votes count
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (reviewer_id) REFERENCES users(id),
            FOREIGN KEY (reviewee_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_reviewee_id ON reviews(reviewee_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_order_id ON reviews(order_id);

        -- ============================================================
        -- REPORTS & DISPUTES
        -- ============================================================
        CREATE TABLE IF NOT EXISTS reports (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id         INTEGER NOT NULL,
            reported_user_id    INTEGER,  -- NULL if reporting a listing
            reported_listing_id INTEGER,  -- NULL if reporting a user
            
            reason              TEXT NOT NULL,  -- spam, fraud, inappropriate, etc.
            description         TEXT,
            
            -- Status
            status              TEXT DEFAULT 'pending',  -- pending, reviewed, resolved, dismissed
            admin_notes         TEXT,
            resolved_by         INTEGER,  -- Admin ID
            resolution          TEXT,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at         TIMESTAMP,
            
            FOREIGN KEY (reporter_id) REFERENCES users(id),
            FOREIGN KEY (reported_user_id) REFERENCES users(id),
            FOREIGN KEY (reported_listing_id) REFERENCES listings(id),
            FOREIGN KEY (resolved_by) REFERENCES admins(id)
        );

        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_reported_user_id ON reports(reported_user_id);

        -- ============================================================
        -- ADMINS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS admins (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id         INTEGER UNIQUE NOT NULL,
            username            TEXT,
            email               TEXT,
            role                TEXT DEFAULT 'moderator',  -- super_admin, admin, moderator
            
            -- Permissions
            can_ban_users       BOOLEAN DEFAULT 1,
            can_feature_listings BOOLEAN DEFAULT 1,
            can_manage_categories BOOLEAN DEFAULT 1,
            can_view_payments   BOOLEAN DEFAULT 1,
            can_manage_admins   BOOLEAN DEFAULT 0,
            
            is_active           BOOLEAN DEFAULT 1,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login          TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_admins_telegram_id ON admins(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_admins_role ON admins(role);

        -- ============================================================
        -- SETTINGS & CONFIGURATION
        -- ============================================================
        CREATE TABLE IF NOT EXISTS settings (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            key                 TEXT NOT NULL UNIQUE,
            value               TEXT,
            data_type           TEXT,  -- string, number, boolean, json
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ============================================================
        -- TRANSACTIONS & PAYMENTS LOG
        -- ============================================================
        CREATE TABLE IF NOT EXISTS transactions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id            INTEGER,
            user_id             INTEGER NOT NULL,
            payment_method      TEXT,  -- stars, usdt, bank_transfer
            amount              REAL NOT NULL,
            currency            TEXT DEFAULT 'USD',
            transaction_type    TEXT,  -- payment, refund, withdrawal, commission
            
            -- External References
            external_id         TEXT,  -- Payment provider transaction ID
            
            -- Status
            status              TEXT DEFAULT 'pending',  -- pending, completed, failed, refunded
            error_message       TEXT,
            
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at        TIMESTAMP,
            
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

        -- ============================================================
        -- FAVORITES & WISHLISTS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS favorites (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL,
            listing_id          INTEGER NOT NULL,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
            UNIQUE(user_id, listing_id)
        );

        CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_favorites_listing_id ON favorites(listing_id);

        -- ============================================================
        -- FOLLOWERS/FOLLOWING
        -- ============================================================
        CREATE TABLE IF NOT EXISTS follows (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id         INTEGER NOT NULL,
            following_id        INTEGER NOT NULL,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(follower_id, following_id)
        );

        CREATE INDEX IF NOT EXISTS idx_follows_follower_id ON follows(follower_id);
        CREATE INDEX IF NOT EXISTS idx_follows_following_id ON follows(following_id);
    """)

    conn.commit()

    # ── Accounts table (social-media accounts for sale) ─────
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id     INTEGER DEFAULT 0,
            name          TEXT    NOT NULL,
            description   TEXT    DEFAULT '',
            price         REAL    NOT NULL DEFAULT 0,
            category      TEXT    DEFAULT 'other',
            status        TEXT    DEFAULT 'available',
            image_path    TEXT    DEFAULT '',
            email         TEXT    DEFAULT '',
            password      TEXT    DEFAULT '',
            followers     INTEGER DEFAULT 0,
            tweets_count  INTEGER DEFAULT 0,
            features      TEXT    DEFAULT '',
            creation_year INTEGER,
            currency      TEXT    DEFAULT 'USD',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
    """)
    conn.commit()
    logger.info("✅ Database schema initialized successfully")

    # Insert default settings
    _init_default_settings(conn)

    # Insert admin
    _init_admin(conn)


def _init_default_settings(conn: sqlite3.Connection) -> None:
    """Initialize default marketplace settings."""
    c = conn.cursor()
    
    defaults = {
        "MARKETPLACE_NAME": ("Telegram Marketplace", "string"),
        "COMMISSION_TYPE": ("percentage", "string"),    # percentage, fixed, both
        "COMMISSION_PERCENT": ("10", "number"),         # 10%
        "COMMISSION_FIXED": ("0", "number"),
        "COMMISSION_MIN": ("0", "number"),
        "COMMISSION_MAX": ("0", "number"),
        
        "TELEGRAM_STARS_ENABLED": ("1", "boolean"),
        "USDT_TRON_ENABLED": ("1", "boolean"),
        "USDT_TRON_ADDRESS": ("TJmRUQ7qhLR22E15Q8egyRyJaFFJxERMxy", "string"),
        
        "BANK_TRANSFER_ENABLED": ("1", "boolean"),
        "BANK_IBAN": ("JO91BJOR0850000013011834606005", "string"),
        "BANK_ACCOUNT_NUMBER": ("0013011834606005", "string"),
        
        "MAINTENANCE_MODE": ("0", "boolean"),
        "REQUIRE_VERIFICATION": ("0", "boolean"),
    }
    
    for key, (value, dtype) in defaults.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value, data_type) VALUES (?, ?, ?)",
            (key, value, dtype)
        )
    
    conn.commit()
    logger.info("✅ Default settings initialized")


def _init_admin(conn: sqlite3.Connection) -> None:
    """Initialize default admin."""
    import os
    
    c = conn.cursor()
    admin_id = int(os.environ.get("ADMIN_ID", "8989271393"))
    admin_username = os.environ.get("ADMIN_USERNAME", "l825h")
    
    c.execute(
        "INSERT OR IGNORE INTO admins (telegram_id, username, role) VALUES (?, ?, ?)",
        (admin_id, admin_username, "super_admin")
    )
    conn.commit()
    logger.info("✅ Admin user initialized")


# ============================================================
# USER OPERATIONS
# ============================================================

def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> Dict:
    """Get or create a user."""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    row = c.fetchone()
    
    if row:
        return dict(row)
    
    c.execute(
        """INSERT INTO users (telegram_id, username, first_name) 
           VALUES (?, ?, ?) RETURNING *""",
        (telegram_id, username, first_name)
    )
    conn.commit()
    return dict(c.fetchone())


def update_user(user_id: int, **kwargs) -> None:
    """Update user profile."""
    allowed = {
        "username", "first_name", "last_name", "avatar_url", "cover_url", "bio",
        "language", "currency", "notification_enabled", "is_verified"
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    
    conn = get_conn()
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = [*updates.values(), user_id]
    conn.execute(
        f"UPDATE users SET {set_clause} WHERE id=?",
        values
    )
    conn.commit()


def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Get user by Telegram ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
    return dict(row) if row else None


# ============================================================
# LISTING OPERATIONS
# ============================================================

def create_listing(seller_id: int, title: str, description: str, category_id: int,
                   platform_id: int, price: float, currency: str = "USD",
                   is_negotiable: bool = True, **kwargs) -> int:
    """Create a new listing."""
    conn = get_conn()
    c = conn.cursor()
    
    # Convert list/dict fields to JSON
    image_urls = json.dumps(kwargs.get("image_urls", []))
    tags = json.dumps(kwargs.get("tags", []))
    extra_details = json.dumps(kwargs.get("extra_details", {}))
    
    c.execute(
        """INSERT INTO listings 
           (seller_id, title, description, category_id, platform_id, price, currency,
            is_negotiable, image_urls, tags, extra_details, main_image_url, country, language)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id""",
        (seller_id, title, description, category_id, platform_id, price, currency,
         is_negotiable, image_urls, tags, extra_details,
         kwargs.get("main_image_url"), kwargs.get("country"), kwargs.get("language"))
    )
    conn.commit()
    return c.lastrowid


def get_listing(listing_id: int) -> Optional[Dict]:
    """Get listing by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if row:
        result = dict(row)
        # Parse JSON fields
        result["image_urls"] = json.loads(result["image_urls"] or "[]")
        result["tags"] = json.loads(result["tags"] or "[]")
        result["extra_details"] = json.loads(result["extra_details"] or "{}")
        return result
    return None


def get_listings(status: str = "active", limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get listings with filters."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM listings WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (status, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def update_listing(listing_id: int, **kwargs) -> None:
    """Update listing."""
    allowed = {
        "title", "description", "price", "currency", "is_negotiable",
        "status", "is_featured", "featured_until", "main_image_url",
        "country", "language", "view_count", "like_count"
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    
    conn = get_conn()
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = [*updates.values(), listing_id]
    conn.execute(
        f"UPDATE listings SET {set_clause} WHERE id=?",
        values
    )
    conn.commit()


# ============================================================
# CHAT OPERATIONS
# ============================================================

def get_or_create_chat(participant_1_id: int, participant_2_id: int, 
                       listing_id: int = None, order_id: int = None) -> Dict:
    """Get or create a chat between two users."""
    conn = get_conn()
    c = conn.cursor()
    
    # Ensure consistent ordering
    p1, p2 = min(participant_1_id, participant_2_id), max(participant_1_id, participant_2_id)
    
    c.execute(
        "SELECT * FROM chats WHERE participant_1_id=? AND participant_2_id=?",
        (p1, p2)
    )
    row = c.fetchone()
    
    if row:
        return dict(row)
    
    c.execute(
        """INSERT INTO chats (participant_1_id, participant_2_id, listing_id, order_id)
           VALUES (?, ?, ?, ?)
           RETURNING *""",
        (p1, p2, listing_id, order_id)
    )
    conn.commit()
    return dict(c.fetchone())


def send_message(chat_id: int, sender_id: int, receiver_id: int, 
                 content: str, message_type: str = "text",
                 media_url: str = None, media_type: str = None,
                 reply_to_id: int = None) -> int:
    """Send a message in a chat."""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute(
        """INSERT INTO messages 
           (chat_id, sender_id, receiver_id, message_type, content, media_url, media_type, reply_to_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id""",
        (chat_id, sender_id, receiver_id, message_type, content, media_url, media_type, reply_to_id)
    )
    conn.commit()
    
    # Update chat last_message info
    conn.execute(
        "UPDATE chats SET last_message_id=?, last_message_at=CURRENT_TIMESTAMP WHERE id=?",
        (c.lastrowid, chat_id)
    )
    conn.commit()
    
    return c.lastrowid


def get_messages(chat_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get messages from a chat."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (chat_id, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_message_as_read(message_id: int) -> None:
    """Mark a message as read."""
    conn = get_conn()
    conn.execute(
        "UPDATE messages SET is_read=1, read_at=CURRENT_TIMESTAMP WHERE id=?",
        (message_id,)
    )
    conn.commit()


# ============================================================
# ORDER OPERATIONS
# ============================================================

def create_order(listing_id: int, buyer_id: int, seller_id: int,
                 amount: float, currency: str = "USD", payment_method: str = None) -> int:
    """Create a new order."""
    conn = get_conn()
    c = conn.cursor()
    
    c.execute(
        """INSERT INTO orders 
           (listing_id, buyer_id, seller_id, amount, currency, payment_method)
           VALUES (?, ?, ?, ?, ?, ?)
           RETURNING id""",
        (listing_id, buyer_id, seller_id, amount, currency, payment_method)
    )
    conn.commit()
    return c.lastrowid


def get_order(order_id: int) -> Optional[Dict]:
    """Get order by ID, joined with account credentials for delivery."""
    conn = get_conn()
    row = conn.execute(
        """SELECT o.*, a.name AS account_name, a.price AS account_price,
                  a.email AS account_email, a.password AS account_password,
                  a.features AS account_features
           FROM orders o
           LEFT JOIN accounts a ON o.listing_id = a.id
           WHERE o.id=?""",
        (order_id,)
    ).fetchone()
    return dict(row) if row else None


def update_order(order_id: int, **kwargs) -> None:
    """Update order."""
    allowed = {"status", "payment_id", "amount", "currency", "commission_amount", "net_amount", "paid_at", "delivered_at", "completed_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    
    conn = get_conn()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = [*updates.values(), order_id]
    conn.execute(
        f"UPDATE orders SET {set_clause} WHERE id=?",
        values
    )
    conn.commit()


# ============================================================
# STATS
# ============================================================

def get_marketplace_stats() -> Dict:
    """Get overall marketplace statistics."""
    conn = get_conn()
    
    def scalar(sql, *args):
        return conn.execute(sql, args).fetchone()[0] or 0
    
    return {
        "total_users": scalar("SELECT COUNT(*) FROM users"),
        "total_listings": scalar("SELECT COUNT(*) FROM listings WHERE status='active'"),
        "total_orders": scalar("SELECT COUNT(*) FROM orders"),
        "completed_orders": scalar("SELECT COUNT(*) FROM orders WHERE status='completed'"),
        "total_revenue": scalar("SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status IN ('paid', 'completed')"),
        "total_commission": scalar("SELECT COALESCE(SUM(commission_amount), 0) FROM orders WHERE status IN ('paid', 'completed')"),
    }


# ============================================================
# ACCOUNTS CRUD (social-media accounts for sale)
# ============================================================

def add_account(name: str, description: str = "", price: float = 0,
                category: str = "other", image_path: str = "",
                email: str = "", password: str = "",
                followers: int = 0, tweets_count: int = 0,
                features: str = "", creation_year: int = None,
                currency: str = "USD", seller_id: int = 0) -> int:
    """Insert a new account listing."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO accounts
           (seller_id, name, description, price, category, image_path,
            email, password, followers, tweets_count, features,
            creation_year, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (seller_id, name, description, price, category, image_path,
         email, password, followers, tweets_count, features,
         creation_year, currency)
    )
    conn.commit()
    return c.lastrowid


def get_account(account_id: int) -> Optional[Dict]:
    """Get a single account by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return dict(row) if row else None


def get_all_accounts(status: str = None) -> List[Dict]:
    """Get all accounts, optionally filtered by status."""
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE status=? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM accounts ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_accounts_admin() -> List[Dict]:
    """Get all accounts for admin (all statuses, includes private data)."""
    return get_all_accounts()


def update_account(account_id: int, **kwargs) -> None:
    """Update account fields."""
    allowed = {
        "name", "description", "price", "category", "status",
        "image_path", "email", "password", "followers", "tweets_count",
        "features", "creation_year", "currency", "seller_id"
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return
    conn = get_conn()
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [account_id]
    conn.execute(f"UPDATE accounts SET {set_clause} WHERE id=?", values)
    conn.commit()


def delete_account(account_id: int) -> None:
    """Delete an account."""
    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()


# ============================================================
# ORDERS HELPERS
# ============================================================

def get_all_orders() -> List[Dict]:
    """Get all orders joined with account details."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, a.name AS account_name, a.price AS account_price,
                  a.email AS account_email, a.password AS account_password,
                  a.features AS account_features
           FROM orders o
           LEFT JOIN accounts a ON o.listing_id = a.id
           ORDER BY o.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_orders() -> List[Dict]:
    """Get pending orders joined with account details."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, a.name AS account_name, a.price AS account_price,
                  a.email AS account_email, a.password AS account_password,
                  a.features AS account_features
           FROM orders o
           LEFT JOIN accounts a ON o.listing_id = a.id
           WHERE o.status='pending'
           ORDER BY o.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> Dict:
    """Get store stats in the format expected by bot_handlers."""
    conn = get_conn()
    def scalar(sql, *args):
        return conn.execute(sql, args).fetchone()[0] or 0

    return {
        "total":         scalar("SELECT COUNT(*) FROM accounts"),
        "available":     scalar("SELECT COUNT(*) FROM accounts WHERE status='available'"),
        "sold":          scalar("SELECT COUNT(*) FROM accounts WHERE status='sold'"),
        "reserved":      scalar("SELECT COUNT(*) FROM accounts WHERE status='reserved'"),
        "revenue":       scalar("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='completed'"),
        "total_orders":  scalar("SELECT COUNT(*) FROM orders"),
        "pending_orders":scalar("SELECT COUNT(*) FROM orders WHERE status='pending'"),
    }


# ============================================================
# Initialize on import
# ============================================================
init_db()
