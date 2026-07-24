-- 0001_create_marketplace_schema.sql
-- Initial marketplace schema for the Telegram Digital Marketplace
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS platforms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT UNIQUE,
  color TEXT,
  icon TEXT,
  banner TEXT,
  illustration TEXT,
  is_other INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT UNIQUE,
  parent_id INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(parent_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  price REAL DEFAULT 0,
  currency TEXT DEFAULT 'USD',
  negotiable INTEGER DEFAULT 0,
  featured INTEGER DEFAULT 0,
  category_id INTEGER,
  platform_id INTEGER,
  platform_other TEXT,
  country TEXT,
  language TEXT,
  condition TEXT,
  extra_details TEXT,
  status TEXT DEFAULT 'active',
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(category_id) REFERENCES categories(id),
  FOREIGN KEY(platform_id) REFERENCES platforms(id)
);

CREATE TABLE IF NOT EXISTS listing_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  alt TEXT,
  position INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS listing_videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  thumb TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS listing_tags (
  listing_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (listing_id, tag_id),
  FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE,
  FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS favorites (
  user_id INTEGER NOT NULL,
  listing_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, listing_id)
);

CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER,
  buyer_id INTEGER NOT NULL,
  seller_id INTEGER NOT NULL,
  is_closed INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(listing_id) REFERENCES listings(id)
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER NOT NULL,
  sender_id INTEGER NOT NULL,
  type TEXT DEFAULT 'text',
  content TEXT,
  attachment_url TEXT,
  reply_to INTEGER,
  status TEXT DEFAULT 'sent',
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
  FOREIGN KEY(reply_to) REFERENCES messages(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id INTEGER,
  filename TEXT,
  url TEXT,
  mime_type TEXT,
  size INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER,
  buyer_id INTEGER,
  seller_id INTEGER,
  amount REAL NOT NULL,
  currency TEXT DEFAULT 'USD',
  commission_fee REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',
  payment_method TEXT,
  tx_ref TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(listing_id) REFERENCES listings(id)
);

CREATE TABLE IF NOT EXISTS commissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  percentage REAL DEFAULT 5.0,
  fixed_fee REAL DEFAULT 0.0,
  min_fee REAL DEFAULT 0.0,
  max_fee REAL DEFAULT 0.0,
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER,
  reviewer_id INTEGER,
  score INTEGER CHECK(score >= 1 AND score <= 5),
  comment TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(listing_id) REFERENCES listings(id)
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  type TEXT,
  payload TEXT,
  is_read INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Full-text search (FTS5) for listings title & description
CREATE VIRTUAL TABLE IF NOT EXISTS listings_fts USING fts5(title, description, content='listings', content_rowid='id');

-- Indexes
CREATE INDEX IF NOT EXISTS idx_listings_seller ON listings(seller_id);
CREATE INDEX IF NOT EXISTS idx_listings_category ON listings(category_id);
CREATE INDEX IF NOT EXISTS idx_listings_platform ON listings(platform_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_seller ON transactions(seller_id);
