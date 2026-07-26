# bot_keyboards.py — All keyboard layouts
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
    # WebApp requires HTTPS; fall back to None for HTTP
    return WebAppInfo(url=url) if (url and url.startswith("https://")) else None


def usd_to_stars(price_usd: float) -> int:
    """Convert USD price to Telegram Stars (1 USD ≈ 50 Stars)."""
    return max(round(price_usd * 50), 1)


# ══════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════
def main_menu_keyboard() -> InlineKeyboardMarkup:
    wa   = _webapp("/")
    base = get_webapp_base()
    admin_username = os.environ.get("ADMIN_USERNAME", "l825h")

    if wa:
        shop_btn = InlineKeyboardButton("🛒  تصفح الحسابات", web_app=wa)
    elif base:
        shop_btn = InlineKeyboardButton("🛒  تصفح الحسابات", url=base + "/")
    else:
        shop_btn = InlineKeyboardButton("🛒  تصفح الحسابات", callback_data="browse_accounts")

    return InlineKeyboardMarkup([
        [shop_btn],
        [
            InlineKeyboardButton("📋  قائمة الحسابات", callback_data="list_accounts"),
            InlineKeyboardButton("🏆  المسابقات",       callback_data="competitions_list"),
        ],
        [
            InlineKeyboardButton("🎁  رابط الدعوة",    callback_data="my_invites"),
            InlineKeyboardButton("📖  طريقة الشراء",   callback_data="how_to_buy"),
        ],
        [
            InlineKeyboardButton("💬  تواصل معنا", url=f"https://t.me/{admin_username}"),
            InlineKeyboardButton("ℹ️  عن المتجر",  callback_data="about"),
        ],
    ])


# ══════════════════════════════════════════════
#  ADMIN KEYBOARD
# ══════════════════════════════════════════════
def admin_keyboard() -> InlineKeyboardMarkup:
    wa   = _webapp("/admin")
    base = get_webapp_base()

    if wa:
        # HTTPS → full Telegram WebApp
        panel_btn = InlineKeyboardButton("🖥️  لوحة التحكم الكاملة", web_app=wa)
    elif base:
        # HTTP (EC2 بدون SSL) → URL button يفتح المتصفح
        panel_btn = InlineKeyboardButton("🖥️  لوحة التحكم الكاملة 🌐", url=base + "/admin")
    else:
        # لا يوجد رابط → أضف WEBAPP_URL في السيكريتس
        panel_btn = InlineKeyboardButton("⚙️  اضبط WEBAPP_URL لفتح اللوحة", callback_data="admin_no_url")

    return InlineKeyboardMarkup([
        [panel_btn],
        [
            InlineKeyboardButton("➕  إضافة حساب",       callback_data="admin_add_start"),
            InlineKeyboardButton("📋  الحسابات",          callback_data="admin_list_0"),
        ],
        [
            InlineKeyboardButton("🏆  المسابقات",         callback_data="admin_competitions"),
            InlineKeyboardButton("👥  المستخدمون",        callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton("📦  الطلبات المعلقة",  callback_data="admin_pending_orders"),
            InlineKeyboardButton("📊  إحصائيات",          callback_data="admin_stats"),
        ],
    ])


# ══════════════════════════════════════════════
#  BACK BUTTONS
# ══════════════════════════════════════════════
def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙  القائمة الرئيسية", callback_data="back_menu")]
    ])


def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙  لوحة التحكم", callback_data="back_admin")]
    ])


# ══════════════════════════════════════════════
#  INVITE LINK KEYBOARD  (جديد)
# ══════════════════════════════════════════════
def invite_keyboard(link: str) -> InlineKeyboardMarkup:
    """Keyboard shown with the personal invite link — includes a share button."""
    rows = []
    if link and link.startswith("http"):
        import urllib.parse
        share_text = urllib.parse.quote("🎁 انضم لمتجر ريبر X عبر رابطي الخاص!")
        share_link = urllib.parse.quote(link)
        rows.append([
            InlineKeyboardButton(
                "📤  مشاركة الرابط",
                url=f"https://t.me/share/url?url={share_link}&text={share_text}"
            )
        ])
    rows.append([InlineKeyboardButton("🔙  القائمة الرئيسية", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════
#  ACCOUNT CARD (user)
# ══════════════════════════════════════════════
def account_card_keyboard(acc_id: int, page: int = 0) -> InlineKeyboardMarkup:
    wa   = _webapp(f"/?account={acc_id}")
    base = get_webapp_base()

    if wa:
        view_btn = InlineKeyboardButton("🔍  تفاصيل كاملة", web_app=wa)
    elif base:
        view_btn = InlineKeyboardButton("🔍  تفاصيل كاملة 🌐", url=base + f"/?account={acc_id}")
    else:
        view_btn = InlineKeyboardButton("🔍  تفاصيل", callback_data=f"detail_{acc_id}")

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒  اشتري هذا الحساب", callback_data=f"buy_{acc_id}")],
        [view_btn],
        [InlineKeyboardButton(f"🔙  رجوع للقائمة", callback_data=f"page_accounts_{page}")],
    ])


# ══════════════════════════════════════════════
#  PAYMENT
# ══════════════════════════════════════════════
def payment_method_keyboard(acc_id: int, price_usd: float) -> InlineKeyboardMarkup:
    stars = usd_to_stars(price_usd)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"⭐ ادفع بالنجوم  ({stars} ⭐)",
                callback_data=f"pay_stars_{acc_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                f"💎 ادفع بـ USDT  (${price_usd:.2f})",
                callback_data=f"pay_usdt_{acc_id}"
            ),
        ],
        [InlineKeyboardButton("❌  إلغاء", callback_data=f"detail_{acc_id}")],
    ])


def usdt_payment_keyboard(order_id: int, address: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  أرسلت المبلغ — إشعار الأدمن", callback_data=f"usdt_sent_{order_id}")],
        [InlineKeyboardButton("❌  إلغاء", callback_data="back_menu")],
    ])


# ══════════════════════════════════════════════
#  USER ACCOUNTS PAGE
# ══════════════════════════════════════════════
def user_accounts_page_keyboard(accounts: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        year = f" ({acc['creation_year']})" if acc.get('creation_year') else ""
        flw  = acc.get('followers', 0) or 0
        flw_txt = f" · {flw//1000}K متابع" if flw >= 1000 else (f" · {flw} متابع" if flw else "")
        rows.append([
            InlineKeyboardButton(
                f"🐦 {acc['name']}{year} — ${acc['price']:.0f}{flw_txt}",
                callback_data=f"detail_{acc['id']}_{page}"
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


# ══════════════════════════════════════════════
#  ADMIN ACCOUNT LIST
# ══════════════════════════════════════════════
def accounts_page_keyboard(accounts: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        icon = {"available": "✅", "sold": "🔴", "reserved": "⏳"}.get(acc['status'], "•")
        rows.append([
            InlineKeyboardButton(
                f"{icon} {acc['name']} — ${acc['price']:.0f}",
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

    rows.append([InlineKeyboardButton("🔙  لوحة التحكم", callback_data="back_admin")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════
#  ADMIN ACCOUNT DETAIL
# ══════════════════════════════════════════════
def admin_account_keyboard(acc_id: int, page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️  تعديل",      callback_data=f"admin_edit_{acc_id}"),
            InlineKeyboardButton("🗑️  حذف",        callback_data=f"admin_del_confirm_{acc_id}"),
        ],
        [
            InlineKeyboardButton("✅  متاح",       callback_data=f"admin_status_{acc_id}_available"),
            InlineKeyboardButton("🔴  مباع",       callback_data=f"admin_status_{acc_id}_sold"),
            InlineKeyboardButton("⏳  محجوز",      callback_data=f"admin_status_{acc_id}_reserved"),
        ],
        [InlineKeyboardButton("🔙  القائمة",       callback_data=f"admin_list_{page}")],
    ])


def admin_delete_confirm_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️  نعم، احذف",  callback_data=f"admin_del_{acc_id}"),
            InlineKeyboardButton("❌  لا، إلغاء",  callback_data=f"admin_account_{acc_id}"),
        ]
    ])


def admin_edit_field_keyboard(acc_id: int) -> InlineKeyboardMarkup:
    fields = [
        ("الاسم",       "name"),
        ("الوصف",       "description"),
        ("السعر",       "price"),
        ("سنة الإنشاء", "creation_year"),
        ("الإيميل",     "email"),
        ("الباسورد",    "password"),
        ("المتابعون",   "followers"),
        ("التغريدات",   "tweets_count"),
        ("المميزات",    "features"),
        ("الصورة",      "photo"),
    ]
    rows = []
    for i in range(0, len(fields), 2):
        row = []
        for label, field in fields[i:i+2]:
            row.append(InlineKeyboardButton(label, callback_data=f"admin_editfield_{acc_id}_{field}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙  رجوع للحساب", callback_data=f"admin_account_{acc_id}")])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════
#  ADMIN ORDER
# ══════════════════════════════════════════════
def admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  تأكيد وتسليم", callback_data=f"admin_confirm_order_{order_id}")],
        [InlineKeyboardButton("❌  رفض الطلب",    callback_data=f"admin_reject_order_{order_id}")],
        [InlineKeyboardButton("🔙  الطلبات",       callback_data="admin_pending_orders")],
    ])


# ══════════════════════════════════════════════
#  COMPETITIONS (user)
# ══════════════════════════════════════════════
def competitions_keyboard(competitions: list) -> InlineKeyboardMarkup:
    rows = []
    for c in competitions:
        rows.append([
            InlineKeyboardButton(
                f"🏆 {c['title']}",
                callback_data=f"competition_{c['id']}"
            )
        ])
    rows.append([InlineKeyboardButton("🔙  القائمة الرئيسية", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)


def competition_detail_keyboard(comp_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁  رابط الدعوة الخاص بي", callback_data=f"comp_mylink_{comp_id}")],
        [InlineKeyboardButton("🏅  المتصدرون", callback_data=f"comp_leaderboard_{comp_id}")],
        [InlineKeyboardButton("🔙  المسابقات",  callback_data="competitions_list")],
    ])


def competition_join_keyboard(comp_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  انضم للمسابقة", callback_data=f"comp_join_{comp_id}")],
        [InlineKeyboardButton("🔙  رجوع",          callback_data="competitions_list")],
    ])


# ══════════════════════════════════════════════
#  ADMIN COMPETITIONS
# ══════════════════════════════════════════════
def admin_competitions_keyboard(competitions: list) -> InlineKeyboardMarkup:
    rows = []
    for c in competitions:
        icon = "🟢" if c['status'] == 'active' else "⚫"
        rows.append([
            InlineKeyboardButton(
                f"{icon} {c['title']}",
                callback_data=f"admin_comp_{c['id']}"
            )
        ])
    rows.append([InlineKeyboardButton("➕  إضافة مسابقة", callback_data="admin_comp_add")])
    rows.append([InlineKeyboardButton("🔙  لوحة التحكم",   callback_data="back_admin")])
    return InlineKeyboardMarkup(rows)


def admin_competition_detail_keyboard(comp_id: int, status: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("✏️  تعديل",         callback_data=f"admin_comp_edit_{comp_id}"),
            InlineKeyboardButton("🗑️  حذف",           callback_data=f"admin_comp_del_confirm_{comp_id}"),
        ],
        [InlineKeyboardButton("🏅  المتصدرون",         callback_data=f"admin_comp_leaderboard_{comp_id}")],
    ]
    if status == 'active':
        rows.append([InlineKeyboardButton("🏁  إنهاء المسابقة", callback_data=f"admin_comp_end_{comp_id}")])
    rows.append([InlineKeyboardButton("🔙  المسابقات",           callback_data="admin_competitions")])
    return InlineKeyboardMarkup(rows)


def admin_comp_delete_confirm_keyboard(comp_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑️  نعم، احذف",  callback_data=f"admin_comp_del_{comp_id}"),
            InlineKeyboardButton("❌  إلغاء",       callback_data=f"admin_comp_{comp_id}"),
        ]
    ])


def admin_comp_edit_field_keyboard(comp_id: int) -> InlineKeyboardMarkup:
    fields = [
        ("العنوان",           "title"),
        ("الوصف",             "description"),
        ("عدد الدعوات",       "required_invites"),
        ("الصورة",            "photo"),
    ]
    rows = []
    for label, field in fields:
        rows.append([InlineKeyboardButton(label, callback_data=f"admin_compfield_{comp_id}_{field}")])
    rows.append([InlineKeyboardButton("🔙  رجوع", callback_data=f"admin_comp_{comp_id}")])
    return InlineKeyboardMarkup(rows)
