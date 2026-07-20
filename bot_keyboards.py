# bot_keyboards.py — Beautiful premium keyboard layouts
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def get_webapp_base() -> str:
    """Resolve the web-app base URL from environment (supports Render, Replit, custom)."""
    for var in ("WEBAPP_URL", "RENDER_EXTERNAL_URL"):
        val = os.environ.get(var, "")
        if val:
            return val.rstrip("/")
    domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if domain:
        return f"https://{domain}"
    return ""


def shop_url(path: str = "") -> str:
    base = get_webapp_base()
    return base + path if base else ""


def _webapp(path: str) -> WebAppInfo | None:
    url = shop_url(path)
    return WebAppInfo(url=url) if url else None


# ───────────────────────────────────────────────
#  Main menu  (shown after /start)
# ───────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    wa = _webapp("/")
    shop_btn = (
        InlineKeyboardButton("🛒  فتح المتجر", web_app=wa)
        if wa else
        InlineKeyboardButton("🛒  فتح المتجر", callback_data="open_shop")
    )
    return InlineKeyboardMarkup([
        [shop_btn],
        [
            InlineKeyboardButton("❓  كيفية الشراء",    callback_data="how_to_buy"),
            InlineKeyboardButton("📞  تواصل معنا",      url="https://t.me/l825h"),
        ],
        [InlineKeyboardButton("⭐  عن المتجر",           callback_data="about")],
    ])


# ───────────────────────────────────────────────
#  Admin keyboard
# ───────────────────────────────────────────────
def admin_keyboard() -> InlineKeyboardMarkup:
    wa = _webapp("/admin")
    panel_btn = (
        InlineKeyboardButton("⚙️  لوحة التحكم", web_app=wa)
        if wa else
        InlineKeyboardButton("⚙️  لوحة التحكم", callback_data="noop")
    )
    return InlineKeyboardMarkup([
        [panel_btn],
        [
            InlineKeyboardButton("📊  الإحصائيات",  callback_data="stats"),
            InlineKeyboardButton("📋  الطلبات",     callback_data="orders_summary"),
        ],
    ])


# ───────────────────────────────────────────────
#  Account card keyboard
# ───────────────────────────────────────────────
def account_card_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    wa = _webapp(f"/?account={acc_id}")
    view_btn = (
        InlineKeyboardButton("🔍  عرض التفاصيل", web_app=wa)
        if wa else
        InlineKeyboardButton("🔍  عرض التفاصيل", callback_data=f"detail_{acc_id}")
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  اشتري الآن",    callback_data=f"buy_{acc_id}")],
        [view_btn],
    ])


# ───────────────────────────────────────────────
#  Back / cancel button
# ───────────────────────────────────────────────
def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙  القائمة الرئيسية", callback_data="back_menu")],
    ])


# ───────────────────────────────────────────────
#  Buy confirmation
# ───────────────────────────────────────────────
def buy_confirm_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅  تأكيد الشراء",  callback_data=f"confirm_buy_{acc_id}"),
            InlineKeyboardButton("❌  إلغاء",          callback_data="back_menu"),
        ],
    ])
