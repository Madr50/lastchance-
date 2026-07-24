# bot_keyboards.py — Beautiful and professional marketplace keyboards
import os
from typing import Optional, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def get_webapp_base() -> str:
    """Get the base URL for the web app."""
    for var in ("WEBAPP_URL", "RENDER_EXTERNAL_URL"):
        val = os.environ.get(var, "")
        if val:
            return val.rstrip("/")
    domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if domain:
        return f"https://{domain}"
    return ""


def shop_url(path: str = "") -> str:
    """Get full URL to shop web app."""
    base = get_webapp_base()
    return base + path if base else ""


def _webapp(path: str) -> Optional[WebAppInfo]:
    """Create WebAppInfo for web app button."""
    url = shop_url(path)
    return WebAppInfo(url=url) if url else None


def usd_to_stars(price_usd: float) -> int:
    """Convert USD price to Telegram Stars (1 USD ≈ 1 Star)."""
    stars = round(price_usd)
    return max(stars, 1)


# ============================================================
# MAIN MENUS
# ============================================================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main marketplace menu."""
    wa = _webapp("/")
    marketplace_btn = (
        InlineKeyboardButton("🏪 تصفح المتجر", web_app=wa)
        if wa else
        InlineKeyboardButton("🏪 تصفح المتجر", callback_data="browse_marketplace")
    )
    admin_username = os.environ.get("ADMIN_USERNAME", "l825h")
    
    return InlineKeyboardMarkup([
        [marketplace_btn],
        [
            InlineKeyboardButton("📋 قائمة المنتجات", callback_data="list_products"),
            InlineKeyboardButton("💰 عرض الأسعار", callback_data="pricing"),
        ],
        [
            InlineKeyboardButton("📖 كيفية الشراء", callback_data="how_to_buy"),
            InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="faq"),
        ],
        [
            InlineKeyboardButton("💬 تواصل معنا", url=f"https://t.me/{admin_username}"),
            InlineKeyboardButton("ℹ️ عن المتجر", callback_data="about"),
        ],
    ])


def seller_menu_keyboard() -> InlineKeyboardMarkup:
    """Seller menu."""
    wa = _webapp("/seller")
    seller_panel = (
        InlineKeyboardButton("📊 لوحة التحكم", web_app=wa)
        if wa else
        InlineKeyboardButton("📊 لوحة التحكم", callback_data="seller_dashboard")
    )
    
    return InlineKeyboardMarkup([
        [seller_panel],
        [
            InlineKeyboardButton("➕ منتج جديد", callback_data="seller_add_product"),
            InlineKeyboardButton("📦 منتجاتي", callback_data="seller_products"),
        ],
        [
            InlineKeyboardButton("📋 طلباتي", callback_data="seller_orders"),
            InlineKeyboardButton("💬 رسائلي", callback_data="seller_chats"),
        ],
        [
            InlineKeyboardButton("🧑‍💼 ملفي الشخصي", callback_data="seller_profile"),
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="seller_settings"),
        ],
    ])


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin dashboard menu."""
    wa = _webapp("/admin")
    admin_panel = (
        InlineKeyboardButton("🖥️ لوحة التحكم الكاملة", web_app=wa)
        if wa else
        InlineKeyboardButton("🖥️ لوحة التحكم", callback_data="admin_dashboard")
    )
    
    return InlineKeyboardMarkup([
        [admin_panel],
        [
            InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users"),
            InlineKeyboardButton("📦 المنتجات", callback_data="admin_products"),
        ],
        [
            InlineKeyboardButton("📋 الطلبات", callback_data="admin_orders"),
            InlineKeyboardButton("💬 الدردشات", callback_data="admin_chats"),
        ],
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("💰 التقارير المالية", callback_data="admin_reports"),
        ],
        [
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings"),
            InlineKeyboardButton("📋 السجلات", callback_data="admin_logs"),
        ],
    ])


# ============================================================
# PRODUCT/LISTING KEYBOARDS
# ============================================================

def listing_detail_keyboard(listing_id: int, seller_id: int, is_seller: bool = False) -> InlineKeyboardMarkup:
    """Detailed keyboard for a single listing."""
    buttons = []
    
    if is_seller:
        buttons.append([
            InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_listing_{listing_id}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_listing_{listing_id}"),
        ])
    else:
        buttons.append([InlineKeyboardButton("🛒 شراء الآن", callback_data=f"buy_listing_{listing_id}")])
    
    buttons.extend([
        [
            InlineKeyboardButton("💬 اتصل بالبائع", callback_data=f"contact_seller_{listing_id}_{seller_id}"),
            InlineKeyboardButton("❤️ أضف للمفضلة", callback_data=f"favorite_listing_{listing_id}"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_list")],
    ])
    
    return InlineKeyboardMarkup(buttons)


def payment_method_keyboard(listing_id: int, price: float) -> InlineKeyboardMarkup:
    """Payment method selection."""
    stars = usd_to_stars(price)
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ نجوم تيليجرام ({stars})", callback_data=f"pay_stars_{listing_id}")],
        [InlineKeyboardButton(f"💎 USDT (${price:.2f})", callback_data=f"pay_usdt_{listing_id}")],
        [InlineKeyboardButton("🏦 تحويل بنكي", callback_data=f"pay_bank_{listing_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_payment")],
    ])


def category_keyboard(categories: List[dict]) -> InlineKeyboardMarkup:
    """Categories selection keyboard."""
    buttons = []
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(
                f"{cat.get('icon', '📦')} {cat['name']}",
                callback_data=f"cat_{cat['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(buttons)


def platform_keyboard(platforms: List[dict]) -> InlineKeyboardMarkup:
    """Platforms selection keyboard."""
    buttons = []
    for plat in platforms:
        buttons.append([
            InlineKeyboardButton(
                f"{plat.get('icon', '🎮')} {plat['name']}",
                callback_data=f"plat_{plat['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# ============================================================
# CHAT KEYBOARDS
# ============================================================

def chat_action_keyboard(chat_id: int, is_muted: bool = False) -> InlineKeyboardMarkup:
    """Chat actions keyboard."""
    mute_text = "🔔 الغاء الكتم" if is_muted else "🔕 كتم الصوت"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(mute_text, callback_data=f"mute_chat_{chat_id}"),
            InlineKeyboardButton("📋 بلاغ", callback_data=f"report_chat_{chat_id}"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_chats")],
    ])


# ============================================================
# ORDER KEYBOARDS
# ============================================================

def order_action_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Order action keyboard based on status."""
    buttons = []
    
    if status == "pending":
        buttons.append([InlineKeyboardButton("✅ تأكيد الاستقبال", callback_data=f"confirm_order_{order_id}")])
    elif status == "completed":
        buttons.append([InlineKeyboardButton("⭐ اكتب تقييم", callback_data=f"review_order_{order_id}")])
    
    buttons.extend([
        [
            InlineKeyboardButton("💬 اتصل بالبائع", callback_data=f"msg_order_{order_id}"),
            InlineKeyboardButton("📋 ابلغ عن مشكلة", callback_data=f"issue_order_{order_id}"),
        ],
        [InlineKeyboardButton("🔙 طلباتي", callback_data="my_orders")],
    ])
    
    return InlineKeyboardMarkup(buttons)


# ============================================================
# PROFILE KEYBOARDS
# ============================================================

def profile_keyboard(user_id: int, is_own: bool = False, is_following: bool = False) -> InlineKeyboardMarkup:
    """User profile keyboard."""
    buttons = []
    
    if not is_own:
        follow_text = "🔕 الغاء المتابعة" if is_following else "🔔 متابعة"
        buttons.append([InlineKeyboardButton(follow_text, callback_data=f"follow_{user_id}")])
        buttons.append([InlineKeyboardButton("💬 أرسل رسالة", callback_data=f"msg_user_{user_id}")])
    else:
        buttons.append([InlineKeyboardButton("✏️ تعديل الملف", callback_data="edit_profile")])
    
    buttons.extend([
        [InlineKeyboardButton("📦 منتجات", callback_data=f"user_products_{user_id}")],
        [InlineKeyboardButton("⭐ التقييمات", callback_data=f"user_reviews_{user_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ])
    
    return InlineKeyboardMarkup(buttons)


# ============================================================
# PAGINATION
# ============================================================

def pagination_keyboard(page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup:
    """Pagination keyboard."""
    buttons = []
    
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}_page_{page-1}"))
    
    nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}_page_{page+1}"))
    
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    
    return InlineKeyboardMarkup(buttons)


# ============================================================
# CONFIRMATION KEYBOARDS
# ============================================================

def confirmation_keyboard(confirm_id: str, confirm_text: str = "تأكيد") -> InlineKeyboardMarkup:
    """Generic confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ {confirm_text}", callback_data=f"confirm_{confirm_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_{confirm_id}"),
        ]
    ])


def delete_confirmation_keyboard(item_id: int, item_type: str) -> InlineKeyboardMarkup:
    """Delete confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ نعم، احذف", callback_data=f"confirm_delete_{item_type}_{item_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_delete_{item_type}_{item_id}"),
        ]
    ])


# ============================================================
# ADMIN KEYBOARDS
# ============================================================

def admin_user_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Admin user management keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ تحقق", callback_data=f"admin_verify_{user_id}"),
            InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_{user_id}"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_users")],
    ])


def admin_listing_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    """Admin listing management keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ مميز", callback_data=f"admin_feature_{listing_id}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"admin_del_listing_{listing_id}"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_products")],
    ])


# ============================================================
# UTILITY KEYBOARDS
# ============================================================

def back_button() -> InlineKeyboardMarkup:
    """Simple back button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])


def cancel_button() -> InlineKeyboardMarkup:
    """Simple cancel button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]])
