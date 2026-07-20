# config.py
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8715509091:AAEaIV-tEfz6KYWwG9vOpTEQ87LrJbxbw_0")
ADMIN_ID = 8989271393
ADMIN_USERNAME = "l825h"
SHOP_NAME = "Twitter X Shop"
DB_NAME = "shop.db"
ACCOUNTS_DIR = "static/images/accounts"

os.makedirs(ACCOUNTS_DIR, exist_ok=True)
