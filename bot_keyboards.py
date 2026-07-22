# bot_keyboards.py — Premium keyboard layouts
import os
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def get_webapp_base() -> str:
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


def _webapp(path: str) -> Optional[WebAppInfo]:
    url = shop_url(path)
    return WebAppInfo(url=url) if url else None


def usd_to_stars(price_usd: float) -> int:
    """Convert USD price to Telegram Stars (1 USD ≈ 50 Stars)."""
    stars = round(price_usd * 50)
    return max(stars, 1)


# ── Main menu (premium layout like reference image) ────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    wa = _webapp("/")
    shop_btn = (
        InlineKeyboardButton("🛒  تصفح حسابات تويتر X", web_app=wa)
        if wa else
        InlineKeyboardButton("🛒  تصفح حسابات تويتر X", callback_data="browse_accounts")
    )
    admin_username = os.environ.get("ADMIN_USERNAME", "l825h")
    return InlineKeyboardMarkup([
        [shop_btn],
        [
            InlineKeyboardButton("📋  قائمة الحسابات", callback_data="list_accounts"),
            InlineKeyboardButton("💰  الأسعار",         callback_data="pricing_info"),
        ],
        [InlineKeyboardButton("📖  طريقة الشراء", callback_data="how_to_buy")],
        [
            InlineKeyboardButton("💬  تواصل معنا", url=f"https://t.me/{admin_username}"),
            InlineKeyboardButton("ℹ️  عن المتجر",  callback_data="about"),
        ],
    ])


# ── Admin main keyboard ────────────────────────────────────
def admin_keyboard() -> InlineKeyboardMarkup:
    wa = _webapp("/admin")
    panel_btn = (
        InlineKeyboardButton("🖥️  لوحة التحكم الكاملة", web_app=wa)
        if wa else
        InlineKeyboardButton("🖥️  لوحة التحكم الكاملة", callback_data="noop")
    )
    return InlineKeyboardMarkup([
        [panel_btn],
        [
            InlineKeyboardButton("➕  إضافة حساب",     callback_data="admin_add_start"),
            InlineKeyboardButton("📋  الحسابات",        callback_data="admin_list_0"),
        ],
        [
            InlineKeyboardButton("📦  الطلبات المعلقة", callback_data="admin_pending_orders"),
            InlineKeyboardButton("📊  إحصائيات",        callback_data="admin_stats"),
        ],
    ])


# ── Account card keyboard (for users) ─────────────────────
def account_card_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    wa = _webapp(f"/?account={acc_id}")
    view_btn = (
        InlineKeyboardButton("🔍  تفاصيل كاملة", web_app=wa)
        if wa else
        InlineKeyboardButton("🔍  تفاصيل كاملة", callback_data=f"detail_{acc_id}")
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  اشتري هذا الحساب", callback_data=f"buy_{acc_id}")],
        [view_btn, InlineKeyboardButton("🔙  رجوع", callback_data="list_accounts")],
    ])


# ── Payment method selection ───────────────────────────────
def payment_method_keyboard(acc_id: int, price_usd: float) -> InlineKeyboardMarkup:
    stars = usd_to_stars(price_usd)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"⭐ ادفع بالنجوم  ({stars} نجمة)",
                callback_data=f"pay_stars_{acc_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"💎 ادفع بـ USDT  (${price_usd:.2f})",
                callback_data=f"pay_usdt_{acc_id}"
            ),
        ],
        [InlineKeyboardButton("❌  إلغاء", callback_data="list_accounts")],
    ])


# ── Buy confirmation (kept for backward compat) ────────────
def buy_confirm_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  تأكيد الشراء", callback_data=f"confirm_buy_{acc_id}")],
        [InlineKeyboardButton("❌  إلغاء",         callback_data="list_accounts")],
    ])


# ── Back to menu ───────────────────────────────────────────
def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠  القائمة الرئيسية", callback_data="back_menu")],
    ])


# ── Admin account management ───────────────────────────────
def admin_account_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️  تعديل",  callback_data=f"admin_edit_{acc_id}"),
            InlineKeyboardButton("🗑️  حذف",   callback_data=f"admin_del_confirm_{acc_id}"),
        ],
        [InlineKeyboardButton("🔙  قائمة الحسابات", callback_data="admin_list_0")],
    ])


def admin_delete_confirm_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️  نعم، احذف", callback_data=f"admin_del_{acc_id}"),
            InlineKeyboardButton("❌  إلغاء",      callback_data=f"admin_account_{acc_id}"),
        ],
    ])


def admin_edit_field_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 الاسم",       callback_data=f"admin_editf_{acc_id}_name"),
            InlineKeyboardButton("📅 سنة الإنشاء", callback_data=f"admin_editf_{acc_id}_creation_year"),
        ],
        [
            InlineKeyboardButton("💰 السعر",       callback_data=f"admin_editf_{acc_id}_price"),
            InlineKeyboardButton("📋 الوصف",       callback_data=f"admin_editf_{acc_id}_description"),
        ],
        [
            InlineKeyboardButton("📧 الإيميل",     callback_data=f"admin_editf_{acc_id}_email"),
            InlineKeyboardButton("🔑 الباسورد",    callback_data=f"admin_editf_{acc_id}_password"),
        ],
        [
            InlineKeyboardButton("👥 المتابعون",   callback_data=f"admin_editf_{acc_id}_followers"),
            InlineKeyboardButton("🐦 التغريدات",   callback_data=f"admin_editf_{acc_id}_tweets_count"),
        ],
        [
            InlineKeyboardButton("⭐ المميزات",    callback_data=f"admin_editf_{acc_id}_features"),
            InlineKeyboardButton("🖼️ الصورة",      callback_data=f"admin_editf_{acc_id}_image"),
        ],
        [
            InlineKeyboardButton("✅ متاح",    callback_data=f"admin_setstatus_{acc_id}_available"),
            InlineKeyboardButton("❌ مباع",    callback_data=f"admin_setstatus_{acc_id}_sold"),
            InlineKeyboardButton("⏳ محجوز",  callback_data=f"admin_setstatus_{acc_id}_reserved"),
        ],
        [InlineKeyboardButton("🔙  رجوع", callback_data=f"admin_account_{acc_id}")],
    ])


# ── Order management (admin) ───────────────────────────────
def admin_order_keyboard(order_id: int, account_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  تأكيد الدفع وإرسال البيانات", callback_data=f"admin_confirm_order_{order_id}")],
        [
            InlineKeyboardButton("❌  رفض الطلب", callback_data=f"admin_reject_order_{order_id}"),
        ],
    ])


def accounts_page_keyboard(accounts: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        status_icon = {"available": "✅", "sold": "🔴", "reserved": "⏳"}.get(acc['status'], "•")
        rows.append([
            InlineKeyboardButton(
                f"{status_icon} {acc['name']} — ${acc['price']:.0f}",
                callback_data=f"admin_account_{acc['id']}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️  السابق", callback_data=f"admin_list_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي  ▶️", callback_data=f"admin_list_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙  القائمة الرئيسية", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)


def user_accounts_page_keyboard(accounts: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        year = f" ({acc['creation_year']})" if acc.get('creation_year') else ""
        rows.append([
            InlineKeyboardButton(
                f"🐦 {acc['name']}{year} — ${acc['price']:.0f}",
                callback_data=f"detail_{acc['id']}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️  السابق", callback_data=f"page_accounts_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي  ▶️", callback_data=f"page_accounts_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙  رجوع للقائمة", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)
