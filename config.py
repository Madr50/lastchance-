# config.py
import os

# ضع توكن البوت هنا
BOT_TOKEN = "ضع_توكن_البوت_هنا"

# معرف الأدمن (Telegram ID تبعك)
ADMIN_ID = 123456789  # غير هذا لرقمك

# اسم المتجر
SHOP_NAME = "Twitter X Shop"

# قاعدة البيانات
DB_NAME = "shop.db"

# مجلد الصور
ACCOUNTS_DIR = "accounts_data"
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
