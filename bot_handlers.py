# bot_handlers.py — Premium bot handlers with beautiful messages
import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID, ADMIN_USERNAME, SHOP_NAME
from database import (
    get_all_accounts, get_account,
    create_order, update_account, get_stats, get_all_orders
)
from bot_keyboards import (
    main_menu_keyboard, admin_keyboard,
    account_card_keyboard, back_to_menu_keyboard, buy_confirm_keyboard
)

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape characters for MarkdownV2."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def _status_label(status: str) -> str:
    return {"available": "✅ متاح", "sold": "❌ مباع", "reserved": "⏳ محجوز"}.get(status, status)


def _divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━"


# ── /start ─────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user  = update.effective_user
    stats = get_stats()
    name  = user.first_name or "صديقي"

    text = (
        f"✨ <b>أهلاً وسهلاً، {name}!</b>\n\n"
        f"🐦 <b>{SHOP_NAME}</b>\n"
        f"{_divider()}\n\n"
        "نحن نوفر أقدم وأندر حسابات تويتر/X الأصيلة:\n\n"
        "  📅  حسابات من عام <b>2010 حتى 2015</b>\n"
        "  ✅  حسابات موثّقة وأصيلة 100٪\n"
        "  ⚡  تسليم فوري بعد التأكيد\n"
        "  🔒  معاملة آمنة ومضمونة\n\n"
        f"{_divider()}\n"
        f"📦  <b>{stats['available']}</b> حساب متاح الآن\n\n"
        "👇 <i>اختر من القائمة للبدء</i>"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


# ── /help ──────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 <b>مساعدة — الأوامر المتاحة</b>\n\n"
        "/start  —  القائمة الرئيسية\n"
        "/shop   —  تصفح الحسابات المتاحة\n"
        "/help   —  هذه الرسالة\n\n"
        "📞 للتواصل مع الأدمن: "
        f"<a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_menu_keyboard()
    )


# ── /shop ──────────────────────────────────────────────────

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    accounts = get_all_accounts(status="available")

    if not accounts:
        await update.message.reply_text(
            "😔 <b>لا توجد حسابات متاحة حالياً</b>\n\n"
            "تابعنا وسيصلك إشعار عند توفر حسابات جديدة 🔔",
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )
        return

    header = (
        f"🛒 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\n"
        f"{_divider()}\n"
        "<i>اضغط على زر الشراء لأي حساب يعجبك</i> 👇"
    )
    await update.message.reply_text(header, parse_mode=ParseMode.HTML)

    for acc in accounts[:10]:
        year_line = f"  📅  سنة الإنشاء: <b>{acc['creation_year']}</b>\n" if acc['creation_year'] else ""
        desc = (acc['description'] or 'لا يوجد وصف')[:200]

        card_text = (
            f"📦 <b>{acc['name']}</b>\n"
            f"{_divider()}\n"
            f"{year_line}"
            f"  💰  السعر: <b>${acc['price']:.2f}</b>\n"
            f"  🏷️  التصنيف: {acc.get('category', 'twitter')}\n"
            f"  {_status_label(acc['status'])}\n\n"
            f"📋 {desc}"
        )

        keyboard = account_card_keyboard(acc['id'])
        img_path = acc.get('image_path')

        try:
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=card_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                continue
        except Exception as e:
            logger.warning(f"Could not send photo for account {acc['id']}: {e}")

        await update.message.reply_text(card_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── /admin ─────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ <b>وصول مرفوض</b>\n\nأنت لست مسؤولاً.",
            parse_mode=ParseMode.HTML
        )
        return

    stats = get_stats()
    text  = _build_stats_text(stats)
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard()
    )


# ── Button Handler ─────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Back to menu ──────────────────────────────────────
    if data == "back_menu":
        user  = query.from_user
        stats = get_stats()
        text  = (
            f"✨ <b>القائمة الرئيسية</b>\n\n"
            f"📦 <b>{stats['available']}</b> حساب متاح الآن\n\n"
            "👇 <i>اختر من القائمة</i>"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard()
        )
        return

    # ── Open shop (fallback when no WebApp URL) ───────────
    if data == "open_shop":
        accounts = get_all_accounts(status="available")
        if not accounts:
            await query.edit_message_text(
                "😔 <b>لا توجد حسابات متاحة الآن.</b>\n\nتابعنا للتحديثات! 🔔",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return
        await query.edit_message_text(
            f"🛒 <b>{len(accounts)} حساب متاح</b>\n\nاستخدم /shop لتصفحها",
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )
        return

    # ── How to buy ────────────────────────────────────────
    if data == "how_to_buy":
        text = (
            "📖 <b>كيفية الشراء — خطوة بخطوة</b>\n"
            f"{_divider()}\n\n"
            "1️⃣  افتح المتجر وتصفح الحسابات المتاحة\n\n"
            "2️⃣  اختر الحساب الذي يناسبك\n\n"
            "3️⃣  اضغط <b>اشتري الآن</b> — ستحصل على رقم الطلب\n\n"
            "4️⃣  تواصل مع الأدمن مع رقم طلبك:\n"
            f"    📞 <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n\n"
            "5️⃣  أتمّ الدفع واستلم بيانات حسابك ⚡\n\n"
            f"{_divider()}\n"
            "✨ <i>سريع، آمن، ومضمون!</i>"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return

    # ── About ─────────────────────────────────────────────
    if data == "about":
        stats = get_stats()
        text  = (
            f"⭐ <b>عن {SHOP_NAME}</b>\n"
            f"{_divider()}\n\n"
            "🐦 متخصصون في حسابات تويتر/X القديمة والنادرة\n"
            "📅 حسابات من 2010 حتى 2015\n"
            "✅ جميع الحسابات أصيلة 100٪\n"
            "🔒 ضمان الجودة والأمان\n\n"
            f"{_divider()}\n"
            f"📊 <b>إحصائياتنا:</b>\n"
            f"  📦 حسابات منضمة: <b>{stats['total']}</b>\n"
            f"  ✅ متاح الآن: <b>{stats['available']}</b>\n"
            f"  🔴 تم بيعها: <b>{stats['sold']}</b>\n\n"
            f"📞 للتواصل: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return

    # ── Stats (admin) ─────────────────────────────────────
    if data == "stats":
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text("⛔ وصول مرفوض.", parse_mode=ParseMode.HTML)
            return
        stats = get_stats()
        await query.edit_message_text(
            _build_stats_text(stats),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )
        return

    # ── Orders summary (admin) ────────────────────────────
    if data == "orders_summary":
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text("⛔ وصول مرفوض.", parse_mode=ParseMode.HTML)
            return
        orders = get_all_orders()
        pending = sum(1 for o in orders if o['status'] == 'pending')
        paid    = sum(1 for o in orders if o['status'] == 'paid')
        done    = sum(1 for o in orders if o['status'] == 'completed')
        text = (
            f"📋 <b>ملخص الطلبات</b>\n"
            f"{_divider()}\n\n"
            f"  🟡 قيد الانتظار: <b>{pending}</b>\n"
            f"  💳 مدفوعة:      <b>{paid}</b>\n"
            f"  ✅ مكتملة:      <b>{done}</b>\n"
            f"  📊 الإجمالي:     <b>{len(orders)}</b>\n\n"
            f"<i>افتح لوحة التحكم لإدارة الطلبات</i>"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard()
        )
        return

    # ── Account detail (fallback) ─────────────────────────
    if data.startswith("detail_"):
        try:
            acc_id  = int(data.split("_", 1)[1])
            account = get_account(acc_id)
        except (ValueError, IndexError):
            account = None

        if not account:
            await query.edit_message_text(
                "❌ الحساب غير موجود.", reply_markup=back_to_menu_keyboard()
            )
            return

        year_line = f"  📅  سنة الإنشاء: <b>{account['creation_year']}</b>\n" if account['creation_year'] else ""
        text = (
            f"🔍 <b>{account['name']}</b>\n"
            f"{_divider()}\n"
            f"{year_line}"
            f"  💰  السعر: <b>${account['price']:.2f}</b>\n"
            f"  🏷️  التصنيف: {account.get('category', 'twitter')}\n"
            f"  {_status_label(account['status'])}\n\n"
            f"📋 {account.get('description') or 'لا يوجد وصف'}"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=account_card_keyboard(acc_id)
        )
        return

    # ── Buy (direct inline) ───────────────────────────────
    if data.startswith("buy_"):
        try:
            acc_id  = int(data.split("_", 1)[1])
            account = get_account(acc_id)
        except (ValueError, IndexError):
            account = None

        if not account or account['status'] != 'available':
            await query.edit_message_text(
                "❌ <b>هذا الحساب لم يعد متاحاً.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return

        # Show confirmation step
        text = (
            f"⚠️ <b>تأكيد الشراء</b>\n"
            f"{_divider()}\n\n"
            f"📦 الحساب: <b>{account['name']}</b>\n"
            f"💰 السعر:  <b>${account['price']:.2f}</b>\n\n"
            "هل تريد المتابعة؟ سيتم حجز الحساب باسمك."
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=buy_confirm_keyboard(acc_id)
        )
        return

    # ── Confirm buy ───────────────────────────────────────
    if data.startswith("confirm_buy_"):
        try:
            acc_id  = int(data.split("_", 2)[2])
            account = get_account(acc_id)
        except (ValueError, IndexError):
            account = None

        if not account or account['status'] != 'available':
            await query.edit_message_text(
                "❌ <b>الحساب لم يعد متاحاً — ربما حجزه شخص آخر.</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return

        buyer_username = query.from_user.username or "unknown"
        order_id       = create_order(acc_id, query.from_user.id, buyer_username)
        update_account(acc_id, status='reserved')

        # Notify admin
        try:
            admin_msg = (
                f"🆕 <b>طلب جديد #{order_id}</b>\n"
                f"{_divider()}\n\n"
                f"📦 الحساب: <b>{account['name']}</b>\n"
                f"💰 السعر:  <b>${account['price']:.2f}</b>\n"
                f"👤 المشتري: @{buyer_username}\n"
                f"🆔 ID: <code>{query.from_user.id}</code>"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")

        success_text = (
            f"✅ <b>تم الطلب بنجاح!</b>\n"
            f"{_divider()}\n\n"
            f"🆔 رقم طلبك: <code>#{order_id}</code>\n"
            f"📦 الحساب:   <b>{account['name']}</b>\n"
            f"💰 المبلغ:    <b>${account['price']:.2f}</b>\n\n"
            f"{_divider()}\n"
            f"📞 تواصل مع الأدمن مع رقم طلبك:\n"
            f"   <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n\n"
            f"⏳ <i>الحساب محجوز لمدة 24 ساعة</i>"
        )
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )
        return

    # ── Unknown ───────────────────────────────────────────
    logger.debug(f"Unknown callback: {data}")


# ── Internal helpers ───────────────────────────────────────

def _build_stats_text(stats: dict) -> str:
    return (
        f"📊 <b>إحصائيات المتجر</b>\n"
        f"{_divider()}\n\n"
        f"  📦 إجمالي الحسابات:  <b>{stats['total']}</b>\n"
        f"  ✅ متاحة:            <b>{stats['available']}</b>\n"
        f"  🔴 مباعة:            <b>{stats['sold']}</b>\n"
        f"  🟡 محجوزة:           <b>{stats['reserved']}</b>\n\n"
        f"  💰 الإيرادات:        <b>${stats['revenue']:.2f}</b>\n"
        f"  📋 الطلبات:          <b>{stats['total_orders']}</b>"
    )
