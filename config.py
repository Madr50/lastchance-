# config.py
import os

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "")
ADMIN_ID       = int(os.environ.get("ADMIN_ID", "8989271393"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "l825h")
SHOP_NAME      = os.environ.get("SHOP_NAME", "Twitter X Shop")
DB_NAME        = os.environ.get("DB_NAME", "shop.db")
ACCOUNTS_DIR   = "static/images/accounts"

# Admin panel password (browser login). Set ADMIN_PASSWORD env var to secure it.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

os.makedirs(ACCOUNTS_DIR, exist_ok=True)
