# config.py — Marketplace Configuration (Environment-based, No hardcoded secrets)
import os
from datetime import datetime

# ============================================================
# TELEGRAM BOT
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8989271393"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "l825h")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

# ============================================================
# MARKETPLACE
# ============================================================
MARKETPLACE_NAME = os.environ.get("MARKETPLACE_NAME", "🏪 LastChance Marketplace")
DB_NAME = os.environ.get("DB_NAME", "shop.db")
ACCOUNTS_DIR = "static/images/accounts"

# ============================================================
# PAYMENT METHODS CONFIGURATION
# ============================================================

# Telegram Stars
TELEGRAM_STARS_ENABLED = os.environ.get("TELEGRAM_STARS_ENABLED", "true").lower() in ("true", "1", "yes")

# USDT (TRON Network - TRC20)
USDT_TRON_ENABLED = os.environ.get("USDT_TRON_ENABLED", "true").lower() in ("true", "1", "yes")
USDT_TRON_ADDRESS = os.environ.get("USDT_TRON_ADDRESS", "TJmRUQ7qhLR22E15Q8egyRyJaFFJxERMxy")

# Bank Transfer (IBAN)
BANK_TRANSFER_ENABLED = os.environ.get("BANK_TRANSFER_ENABLED", "true").lower() in ("true", "1", "yes")
BANK_IBAN = os.environ.get("BANK_IBAN", "JO91BJOR0850000013011834606005")
BANK_ACCOUNT_NUMBER = os.environ.get("BANK_ACCOUNT_NUMBER", "0013011834606005")
BANK_ACCOUNT_OWNER = os.environ.get("BANK_ACCOUNT_OWNER", "")
BANK_NAME = os.environ.get("BANK_NAME", "")

# ============================================================
# COMMISSION SYSTEM
# ============================================================
COMMISSION_TYPE = os.environ.get("COMMISSION_TYPE", "percentage")  # percentage, fixed, both
COMMISSION_PERCENT = float(os.environ.get("COMMISSION_PERCENT", "10"))  # 10%
COMMISSION_FIXED = float(os.environ.get("COMMISSION_FIXED", "0"))  # Fixed fee
COMMISSION_MIN = float(os.environ.get("COMMISSION_MIN", "0"))  # Minimum commission
COMMISSION_MAX = float(os.environ.get("COMMISSION_MAX", "0"))  # Maximum commission (0 = no limit)

# ============================================================
# FEATURES & SETTINGS
# ============================================================
MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE", "false").lower() in ("true", "1", "yes")
REQUIRE_VERIFICATION = os.environ.get("REQUIRE_VERIFICATION", "false").lower() in ("true", "1", "yes")
REQUIRE_EMAIL_VERIFICATION = os.environ.get("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("true", "1", "yes")

# ============================================================
# PAGINATION
# ============================================================
ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", "20"))
LISTINGS_PER_PAGE = int(os.environ.get("LISTINGS_PER_PAGE", "12"))

# ============================================================
# SECURITY
# ============================================================
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "3600"))  # 1 hour

# ============================================================
# STORAGE & FILES
# ============================================================
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "10485760"))  # 10 MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "pdf", "doc", "docx", "zip"}

# ============================================================
# DIRECTORY SETUP
# ============================================================
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/listings", exist_ok=True)
os.makedirs("static/avatars", exist_ok=True)
os.makedirs("static/covers", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# ============================================================
# LOGGING
# ============================================================
LOG_FILE = "logs/marketplace.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_payment_methods():
    """Get enabled payment methods."""
    methods = []
    if TELEGRAM_STARS_ENABLED:
        methods.append({
            "id": "stars",
            "name": "⭐ Telegram Stars",
            "icon": "⭐",
            "enabled": True
        })
    if USDT_TRON_ENABLED:
        methods.append({
            "id": "usdt",
            "name": "💎 USDT (TRON)",
            "icon": "💎",
            "enabled": True,
            "address": USDT_TRON_ADDRESS
        })
    if BANK_TRANSFER_ENABLED:
        methods.append({
            "id": "bank",
            "name": "🏦 Bank Transfer",
            "icon": "🏦",
            "enabled": True,
            "iban": BANK_IBAN,
            "account_number": BANK_ACCOUNT_NUMBER
        })
    return methods


def calculate_commission(amount: float) -> dict:
    """Calculate commission for an amount."""
    if COMMISSION_TYPE == "percentage":
        commission = amount * (COMMISSION_PERCENT / 100)
    elif COMMISSION_TYPE == "fixed":
        commission = COMMISSION_FIXED
    else:  # both
        commission = max(COMMISSION_FIXED, amount * (COMMISSION_PERCENT / 100))
    
    # Apply min/max
    if COMMISSION_MIN > 0:
        commission = max(commission, COMMISSION_MIN)
    if COMMISSION_MAX > 0:
        commission = min(commission, COMMISSION_MAX)
    
    return {
        "gross_amount": amount,
        "commission": round(commission, 2),
        "net_amount": round(amount - commission, 2),
        "commission_percent": COMMISSION_PERCENT
    }


def get_payment_info():
    """Get payment information for displaying to users."""
    info = {
        "methods": get_payment_methods(),
        "commission": {
            "type": COMMISSION_TYPE,
            "percent": COMMISSION_PERCENT,
            "fixed": COMMISSION_FIXED,
            "min": COMMISSION_MIN,
            "max": COMMISSION_MAX
        }
    }
    return info
