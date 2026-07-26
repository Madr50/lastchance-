# config.py — all settings from environment variables (NO unsafe defaults)
import os
import sys

def _require(key: str) -> str:
    """Get env var or exit with a clear error message."""
    val = os.environ.get(key, "").strip()
    if not val:
        print(
            f"\n❌ FATAL: Environment variable '{key}' is required but not set.\n"
            f"   Go to Replit Secrets (🔒) and add '{key}'.\n"
            f"   The bot will NOT start until all required secrets are configured.\n",
            file=sys.stderr
        )
        sys.exit(1)
    return val


# ── Required secrets ──────────────────────────────────────────────────────────
BOT_TOKEN      = _require("BOT_TOKEN")
ADMIN_PASSWORD = _require("ADMIN_PASSWORD")   # Browser admin panel login

# ── Optional with safe defaults ────────────────────────────────────────────────
BOT_USERNAME   = os.environ.get("BOT_USERNAME", "")
ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0") or "0")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
SHOP_NAME      = os.environ.get("SHOP_NAME", "متجر ريبر X | حسابات X النادرة")
DB_NAME        = os.environ.get("DB_NAME", "shop.db")
ACCOUNTS_DIR   = "static/images/accounts"

# عنوان USDT Optimism لاستقبال المدفوعات
USDT_ADDRESS = os.environ.get("USDT_ADDRESS", "0xfcbc4e43506fd1c16175d3beb1e25c164d780fba")

# Number of invites required to win a competition
COMPETITION_REQUIRED_INVITES = int(os.environ.get("COMPETITION_REQUIRED_INVITES", "15"))

os.makedirs(ACCOUNTS_DIR, exist_ok=True)
