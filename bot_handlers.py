# bot_handlers.py — Complete premium bot with Stars + USDT payments
import logging
import os
from telegram import Update, InputMediaPhoto, LabeledPrice
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID, ADMIN_USERNAME, SHOP_NAME, USDT_ADDRESS
from database import (
    get_all_accounts, get_account, get_all_accounts_admin,
    create_order, update_account, delete_account,
    get_stats, get_all_orders, get_pending_orders,
    get_order, update_order, add_account
)
from bot_keyboards import (
    main_menu_keyboard, admin_keyboard,
    account_card_keyboard, back_to_menu_keyboard,
    payment_method_keyboard,
    admin_account_keyboard, admin_delete_confirm_keyboard,
    admin_edit_field_keyboard, admin_order_keyboard,
    accounts_page_keyboard, user_accounts_page_keyboard,
    usd_to_stars
)

logger = logging.getLogger(__name__)

# ── State keys ─────────────────────────────────────────────
STATE        = "bot_state"
DRAFT        = "bot_draft"
EDIT_ID      = "edit_acc_id"
EDIT_FIELD   = "edit_field"

# States
S_IDLE          = "idle"
S_ADD_NAME      = "add_name"
S_ADD_YEAR      = "add_year"
S_ADD_PRICE     = "add_price"
S_ADD_EMAIL     = "add_email"
S_ADD_PASSWORD  = "add_password"
S_ADD_FOLLOWERS = "add_followers"
S_ADD_TWEETS    = "add_tweets"
S_ADD_FEATURES  = "add_features"
S_ADD_DESC      = "add_desc"
S_ADD_PHOTO     = "add_photo"
S_EDIT_VALUE    = "edit_value"
S_EDIT_PHOTO    = "edit_photo"

PAGE_SIZE = 5


# ── Helpers ────────────────────────────────────────────────

def _divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━━━━━"

def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def _status_icon(status: str) -> str:
    return {"available": "✅", "sold": "🔴", "reserved": "⏳"}.get(status, "•")

def _status_label(status: str) -> str:
    return {"available": "✅ متاح للبيع", "sold": "🔴 تم البيع", "reserved": "⏳ محجوز"}.get(status, status)

def _fmt_num(n) -> str:
    """Format large numbers like 12500 → 12.5K"""
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

def _account_card(acc: dict, show_private: bool = False) -> str:
    year  = f"  📅  سنة الإنشاء: <b>{acc['creation_year']}</b>\n" if acc.get('creation_year') else ""
    desc  = (acc.get('description') or '')[:300]
    feat  = acc.get('features') or ''
    flw   = _fmt_num(acc.get('followers', 0))
    twts  = _fmt_num(acc.get('tweets_count', 0))

    feat_line = f"\n⭐ <b>المميزات:</b> {feat}\n" if feat else ""

    stats_line = ""
    if int(acc.get('followers', 0)) or int(acc.get('tweets_count', 0)):
        stats_line = f"  👥  متابعون: <b>{flw}</b>   🐦  تغريدات: <b>{twts}</b>\n"

    private = ""
    if show_private:
        email = acc.get('email') or '—'
        pw    = acc.get('password') or '—'
        private = (
            f"\n{_divider()}\n"
            f"🔐 <b>بيانات الدخول (خاص):</b>\n"
            f"  📧 الإيميل:  <code>{email}</code>\n"
            f"  🔑 الباسورد: <code>{pw}</code>\n"
        )

    return (
        f"🐦 <b>{acc['name']}</b>\n"
        f"{_divider()}\n"
        f"{year}"
        f"{stats_line}"
        f"  💰  السعر: <b>${acc['price']:.2f}</b>\n"
        f"  {_status_label(acc['status'])}\n"
        f"{feat_line}"
        f"\n📋 {desc}{private}"
    )

def _build_stats_text(stats: dict) -> str:
    return (
        f"📊 <b>إحصائيات المتجر</b>\n"
        f"{_divider()}\n\n"
        f"  📦  إجمالي الحسابات:  <b>{stats['total']}</b>\n"
        f"  ✅  متاحة:            <b>{stats['available']}</b>\n"
        f"  🔴  مباعة:            <b>{stats['sold']}</b>\n"
        f"  ⏳  محجوزة:          <b>{stats['reserved']}</b>\n\n"
        f"  💰  الإيرادات:       <b>${stats['revenue']:.2f}</b>\n"
        f"  📋  الطلبات:         <b>{stats['total_orders']}</b>\n"
        f"  🟡  طلبات معلقة:     <b>{stats['pending_orders']}</b>"
    )


async def _deliver_account(bot, buyer_id: int, order: dict) -> bool:
    """Send account credentials to the buyer. Returns True on success."""
    email    = order.get('account_email') or '—'
    password = order.get('account_password') or '—'
    features = order.get('account_features') or ''

    msg = (
        f"🎉 <b>مبروك! تم تأكيد دفعك</b>\n"
        f"{_divider()}\n\n"
        f"📦 الحساب: <b>{order.get('account_name', '—')}</b>\n\n"
        f"{_divider()}\n"
        f"🔐 <b>بيانات دخول حسابك:</b>\n\n"
        f"📧 الإيميل:  <code>{email}</code>\n"
        f"🔑 الباسورد: <code>{password}</code>\n\n"
    )
    if features:
        msg += f"⭐ المميزات: {features}\n\n"
    msg += (
        f"{_divider()}\n"
        f"📞 للدعم: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n\n"
        "✨ <i>شكراً لثقتك بنا — استمتع بحسابك!</i>"
    )
    try:
        await bot.send_message(chat_id=buyer_id, text=msg, parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        logger.warning(f"Could not deliver credentials to {buyer_id}: {e}")
        return False


# ── /start ─────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user  = update.effective_user
    stats = get_stats()
    name  = user.first_name or "صديقي"

    context.user_data.clear()

    text = (
        f"✨ <b>أهلاً وسهلاً، {name}!</b>\n\n"
        f"🐦 <b>{SHOP_NAME}</b>\n"
        f"{_divider()}\n\n"
        "🌟 <b>متجرك الموثوق لحسابات تويتر/X الأصيلة القديمة</b>\n\n"
        "  📅  حسابات من عام <b>2006 حتى 2015</b>\n"
        "  ✅  موثّقة وأصيلة <b>100٪</b>\n"
        "  ⚡  تسليم فوري بعد تأكيد الدفع\n"
        "  🔒  ضمان الجودة والأمان التام\n"
        "  💎  أندر الحسابات وأقدمها\n\n"
        f"  ⭐  ادفع بنجوم تيليجرام — تسليم <b>فوري تلقائي</b>\n"
        f"  💎  ادفع بـ USDT TRC20\n\n"
        f"{_divider()}\n"
        f"📦  <b>{stats['available']}</b> حساب متاح الآن\n\n"
        "👇 <i>اختر من القائمة أدناه للبدء</i>"
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


# ── /help ──────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 <b>الأوامر المتاحة</b>\n"
        f"{_divider()}\n\n"
        "/start  —  القائمة الرئيسية\n"
        "/shop   —  تصفح الحسابات المتاحة\n"
        "/help   —  هذه الرسالة\n\n"
        f"📞 للتواصل المباشر مع الأدمن:\n"
        f"   <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
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
    await _send_accounts_page(update.message, accounts, 0)


# ── /admin ─────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "⛔ <b>وصول مرفوض</b>\n\nهذا الأمر للمسؤول فقط.",
            parse_mode=ParseMode.HTML
        )
        return
    context.user_data.clear()
    stats = get_stats()
    await update.message.reply_text(
        _build_stats_text(stats),
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard()
    )


# ── /cancel ────────────────────────────────────────────────

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ <b>تم إلغاء العملية</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard() if not _is_admin(update.effective_user.id) else admin_keyboard()
    )


# ── Successful Payment Handler (Telegram Stars) ────────────

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called automatically when a Stars payment succeeds."""
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # format: "acc_{acc_id}_{buyer_id}"

    try:
        parts  = payload.split("_")
        acc_id = int(parts[1])
        buyer_id = int(parts[2])
    except (IndexError, ValueError):
        logger.error(f"Bad Stars payment payload: {payload}")
        await update.message.reply_text(
            "✅ <b>تم استلام دفعتك!</b>\n\n"
            f"تواصل مع الأدمن: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>",
            parse_mode=ParseMode.HTML
        )
        return

    account = get_account(acc_id)
    if not account:
        logger.error(f"Stars payment for nonexistent account {acc_id}")
        await update.message.reply_text(
            "✅ <b>تم استلام دفعتك!</b>\n\n"
            f"تواصل مع الأدمن: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>",
            parse_mode=ParseMode.HTML
        )
        return

    user           = update.effective_user
    buyer_username = user.username or "unknown"
    order_id       = create_order(acc_id, buyer_id, buyer_username)
    update_account(acc_id, status='sold')
    update_order(order_id, 'completed')

    # Deliver credentials immediately
    order = get_order(order_id)
    delivered = await _deliver_account(context.bot, buyer_id, order)

    # Notify admin
    stars_paid = payment.total_amount
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"⭐ <b>دفع بالنجوم — تم التسليم التلقائي!</b>\n"
                f"{_divider()}\n\n"
                f"🆔 الطلب:    <code>#{order_id}</code>\n"
                f"📦 الحساب:  <b>{account['name']}</b>\n"
                f"💰 السعر:   <b>${account['price']:.2f}</b>\n"
                f"⭐ النجوم:  <b>{stars_paid}</b>\n"
                f"👤 المشتري: @{buyer_username}  (<code>{buyer_id}</code>)\n\n"
                f"{'📬 تم إرسال بيانات الدخول للمشتري ⚡' if delivered else '⚠️ فشل الإرسال التلقائي — أرسل البيانات يدوياً'}"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Could not notify admin of Stars payment: {e}")


# ── Pre-Checkout Query Handler ─────────────────────────────

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve all pre-checkout queries for Stars payments."""
    query = update.pre_checkout_query
    try:
        parts  = query.invoice_payload.split("_")
        acc_id = int(parts[1])
        account = get_account(acc_id)
        if account and account['status'] == 'available':
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="❌ عذراً، هذا الحساب لم يعد متاحاً.")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await query.answer(ok=False, error_message="❌ حدث خطأ، تواصل مع الأدمن.")


# ── Message Handler (admin conversation) ──────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages during admin conversation flows."""
    user  = update.effective_user
    state = context.user_data.get(STATE, S_IDLE)

    if state == S_IDLE:
        return

    if not _is_admin(user.id):
        return

    text = (update.message.text or "").strip()

    # ── ADD ACCOUNT FLOW ──────────────────────────────────
    if state == S_ADD_NAME:
        context.user_data[DRAFT]["name"] = text
        context.user_data[STATE] = S_ADD_YEAR
        await update.message.reply_text(
            "📅 <b>سنة الإنشاء</b>\n\nأدخل سنة إنشاء الحساب (مثال: 2010)\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_YEAR:
        if text == "-":
            context.user_data[DRAFT]["creation_year"] = None
        elif text.isdigit() and 2006 <= int(text) <= 2025:
            context.user_data[DRAFT]["creation_year"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل سنة صحيحة بين 2006 و2025، أو أرسل <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_PRICE
        await update.message.reply_text(
            "💰 <b>السعر بالدولار</b>\n\nأدخل السعر (مثال: 25.00)",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_PRICE:
        try:
            price = float(text)
            assert price >= 0
        except (ValueError, AssertionError):
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً للسعر (مثال: 25)")
            return
        context.user_data[DRAFT]["price"] = price
        context.user_data[STATE] = S_ADD_EMAIL
        await update.message.reply_text(
            "📧 <b>إيميل الحساب</b>\n\nأدخل إيميل الحساب\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_EMAIL:
        context.user_data[DRAFT]["email"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_PASSWORD
        await update.message.reply_text(
            "🔑 <b>باسورد الحساب</b>\n\nأدخل باسورد الحساب\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_PASSWORD:
        context.user_data[DRAFT]["password"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_FOLLOWERS
        await update.message.reply_text(
            "👥 <b>عدد المتابعين</b>\n\nأدخل عدد المتابعين (مثال: 1500)\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_FOLLOWERS:
        if text == "-":
            context.user_data[DRAFT]["followers"] = 0
        elif text.isdigit():
            context.user_data[DRAFT]["followers"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_TWEETS
        await update.message.reply_text(
            "🐦 <b>عدد التغريدات</b>\n\nأدخل عدد التغريدات\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_TWEETS:
        if text == "-":
            context.user_data[DRAFT]["tweets_count"] = 0
        elif text.isdigit():
            context.user_data[DRAFT]["tweets_count"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_FEATURES
        await update.message.reply_text(
            "⭐ <b>المميزات الخاصة</b>\n\nاكتب مميزات الحساب (مثال: حساب نادر، بدون رقم هاتف، OG username)\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_FEATURES:
        context.user_data[DRAFT]["features"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_DESC
        await update.message.reply_text(
            "📋 <b>الوصف</b>\n\nأدخل وصفاً للحساب\nأو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_DESC:
        context.user_data[DRAFT]["description"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_PHOTO
        await update.message.reply_text(
            "🖼️ <b>صورة الحساب</b>\n\nأرسل صورة للحساب (للتوثيق)\nأو أرسل <code>-</code> لإضافة الحساب بدون صورة",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_PHOTO:
        if text == "-":
            context.user_data[DRAFT]["image_path"] = None
            await _finalize_add_account(update, context)
        else:
            await update.message.reply_text(
                "⚠️ أرسل صورة للحساب، أو أرسل <code>-</code> للتخطي بدون صورة",
                parse_mode=ParseMode.HTML
            )

    # ── EDIT FIELD VALUE ──────────────────────────────────
    elif state == S_EDIT_VALUE:
        acc_id = context.user_data.get(EDIT_ID)
        field  = context.user_data.get(EDIT_FIELD)
        acc    = get_account(acc_id)
        if not acc:
            await update.message.reply_text("❌ الحساب غير موجود")
            context.user_data.clear()
            return

        value = text
        try:
            if field == "price":
                value = float(text)
            elif field == "creation_year":
                value = int(text) if text.isdigit() else None
            elif field in ("followers", "tweets_count"):
                value = int(text) if text.isdigit() else 0
        except (ValueError, TypeError):
            await update.message.reply_text("⚠️ قيمة غير صحيحة، حاول مرة أخرى")
            return

        if text == "-":
            value = None if field == "creation_year" else ""

        update_account(acc_id, **{field: value})
        context.user_data.clear()
        acc = get_account(acc_id)

        field_labels = {
            "name": "الاسم", "price": "السعر", "creation_year": "سنة الإنشاء",
            "description": "الوصف", "email": "الإيميل", "password": "الباسورد",
            "followers": "المتابعون", "tweets_count": "التغريدات", "features": "المميزات"
        }
        await update.message.reply_text(
            f"✅ <b>تم تحديث {field_labels.get(field, field)}</b>\n\n" + _account_card(acc, show_private=True),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_edit_field_keyboard(acc_id)
        )


# ── Photo Handler ──────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user  = update.effective_user
    if not _is_admin(user.id):
        return

    state = context.user_data.get(STATE, S_IDLE)

    if state == S_ADD_PHOTO:
        photo  = update.message.photo[-1]
        bot    = context.bot

        photo_file = await bot.get_file(photo.file_id)
        import time
        filename  = f"{int(time.time())}_{photo.file_id[:8]}.jpg"
        save_path = f"static/images/accounts/{filename}"
        os.makedirs("static/images/accounts", exist_ok=True)
        await photo_file.download_to_drive(save_path)

        context.user_data[DRAFT]["image_path"] = save_path
        await _finalize_add_account(update, context)

    elif state == S_EDIT_PHOTO:
        acc_id = context.user_data.get(EDIT_ID)
        photo  = update.message.photo[-1]
        bot    = context.bot

        photo_file = await bot.get_file(photo.file_id)
        import time
        filename  = f"{int(time.time())}_{photo.file_id[:8]}.jpg"
        save_path = f"static/images/accounts/{filename}"
        os.makedirs("static/images/accounts", exist_ok=True)
        await photo_file.download_to_drive(save_path)

        update_account(acc_id, image_path=save_path)
        context.user_data.clear()
        acc = get_account(acc_id)
        await update.message.reply_photo(
            photo=open(save_path, 'rb'),
            caption=f"✅ <b>تم تحديث صورة الحساب</b>\n\n" + _account_card(acc, show_private=True),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_edit_field_keyboard(acc_id)
        )


async def _finalize_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    draft = context.user_data.get(DRAFT, {})
    acc_id = add_account(
        name         = draft.get("name", "حساب جديد"),
        description  = draft.get("description", ""),
        price        = draft.get("price", 0),
        creation_year= draft.get("creation_year"),
        category     = "twitter",
        image_path   = draft.get("image_path"),
        email        = draft.get("email", ""),
        password     = draft.get("password", ""),
        followers    = draft.get("followers", 0),
        tweets_count = draft.get("tweets_count", 0),
        features     = draft.get("features", ""),
    )
    context.user_data.clear()
    acc = get_account(acc_id)

    text = (
        f"🎉 <b>تم إضافة الحساب بنجاح!</b>\n"
        f"🆔 رقم الحساب: <code>{acc_id}</code>\n\n"
        + _account_card(acc, show_private=True)
    )

    if acc.get("image_path") and os.path.exists(acc["image_path"]):
        await update.message.reply_photo(
            photo=open(acc["image_path"], 'rb'),
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=admin_account_keyboard(acc_id)
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=admin_account_keyboard(acc_id)
        )


# ── Helper: send accounts page ─────────────────────────────

async def _send_accounts_page(target, accounts: list, page: int, is_admin: bool = False) -> None:
    total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = max(0, min(page, total_pages - 1))
    chunk       = accounts[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    if not accounts:
        text = "😔 <b>لا توجد حسابات متاحة حالياً</b>"
        kb   = back_to_menu_keyboard()
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    header = (
        f"{'📋 <b>جميع الحسابات</b>' if is_admin else '🛒 <b>الحسابات المتاحة</b>'}"
        f"  ({len(accounts)} حساب)\n"
        f"{_divider()}\n"
        f"الصفحة {page+1} من {total_pages}\n\n"
        "<i>اختر حساباً لعرض تفاصيله</i>"
    )

    if is_admin:
        kb = accounts_page_keyboard(chunk, page, total_pages)
    else:
        kb = user_accounts_page_keyboard(chunk, page, total_pages)

    await target.reply_text(header, parse_mode=ParseMode.HTML, reply_markup=kb)


# ── Button Handler ─────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = query.from_user

    # ── Back to main menu ─────────────────────────────────
    if data == "back_menu":
        context.user_data.clear()
        stats = get_stats()
        if _is_admin(user.id):
            await query.edit_message_text(
                _build_stats_text(stats),
                parse_mode=ParseMode.HTML,
                reply_markup=admin_keyboard()
            )
        else:
            await query.edit_message_text(
                f"✨ <b>القائمة الرئيسية — {SHOP_NAME}</b>\n\n"
                f"📦 <b>{stats['available']}</b> حساب متاح الآن\n\n"
                "👇 <i>اختر من القائمة</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_keyboard()
            )
        return

    # ── Browse / list accounts (user) ─────────────────────
    if data in ("browse_accounts", "list_accounts"):
        accounts = get_all_accounts(status="available")
        if not accounts:
            await query.edit_message_text(
                "😔 <b>لا توجد حسابات متاحة حالياً</b>\n\nتابعنا للتحديثات! 🔔",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        chunk = accounts[:PAGE_SIZE]
        header = (
            f"🛒 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\n"
            f"{_divider()}\n"
            f"الصفحة 1 من {total_pages}\n\n"
            "<i>اختر حساباً لعرض تفاصيله</i>"
        )
        await query.edit_message_text(
            header,
            parse_mode=ParseMode.HTML,
            reply_markup=user_accounts_page_keyboard(chunk, 0, total_pages)
        )
        return

    # ── Paginate user accounts ────────────────────────────
    if data.startswith("page_accounts_"):
        page     = int(data.split("_")[-1])
        accounts = get_all_accounts(status="available")
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        page    = max(0, min(page, total_pages - 1))
        chunk   = accounts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        header  = (
            f"🛒 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\n"
            f"{_divider()}\n"
            f"الصفحة {page+1} من {total_pages}\n\n"
            "<i>اختر حساباً لعرض تفاصيله</i>"
        )
        await query.edit_message_text(
            header,
            parse_mode=ParseMode.HTML,
            reply_markup=user_accounts_page_keyboard(chunk, page, total_pages)
        )
        return

    # ── Pricing info ──────────────────────────────────────
    if data == "pricing_info":
        accounts = get_all_accounts(status="available")
        if accounts:
            prices = [a['price'] for a in accounts]
            min_p, max_p = min(prices), max(prices)
            price_range = f"<b>${min_p:.0f}</b> — <b>${max_p:.0f}</b>"
        else:
            price_range = "راجع قائمة الحسابات"

        text = (
            f"💰 <b>نظام الأسعار</b>\n"
            f"{_divider()}\n\n"
            f"🏷️ نطاق الأسعار الحالي: {price_range}\n\n"
            "📌 <b>عوامل تحديد السعر:</b>\n"
            "  📅  قِدَم الحساب (كلما كان أقدم، كان أغلى)\n"
            "  👥  عدد المتابعين\n"
            "  🐦  تاريخ النشاط\n"
            "  ⭐  مميزات خاصة (OG username، وغيرها)\n\n"
            "✅ <b>جميع الأسعار تشمل:</b>\n"
            "  • ضمان أصالة الحساب\n"
            "  • تسليم فوري بعد الدفع\n"
            "  • دعم ما بعد البيع\n\n"
            f"{_divider()}\n"
            "⭐ <b>الدفع بالنجوم:</b> تسليم فوري تلقائي 100٪\n"
            "💎 <b>الدفع بـ USDT:</b> تسليم فور تأكيد الأدمن"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return

    # ── How to buy ────────────────────────────────────────
    if data == "how_to_buy":
        text = (
            "📖 <b>كيفية الشراء — خطوة بخطوة</b>\n"
            f"{_divider()}\n\n"
            "1️⃣  تصفح الحسابات المتاحة من القائمة\n\n"
            "2️⃣  اختر الحساب الذي يناسبك واضغط <b>اشتري</b>\n\n"
            "3️⃣  اختر طريقة الدفع:\n\n"
            "   ⭐ <b>نجوم تيليجرام</b>\n"
            "      • ادفع مباشرة داخل التطبيق\n"
            "      • تسليم بيانات الحساب <b>فوراً وتلقائياً</b> ⚡\n\n"
            "   💎 <b>USDT TRC20</b>\n"
            "      • أرسل المبلغ للعنوان المحدد\n"
            "      • أرسل صورة الإيصال للأدمن مع رقم طلبك\n"
            f"      • 📞 <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n"
            "      • يؤكد الأدمن ويرسل البيانات <b>فوراً</b>\n\n"
            f"{_divider()}\n"
            "✨ <i>سريع · آمن · مضمون</i>"
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
            "📅 حسابات من 2006 حتى 2015\n"
            "✅ جميع الحسابات أصيلة 100٪ ومضمونة\n"
            "🔒 تسليم آمن وفوري بعد تأكيد الدفع\n\n"
            f"{_divider()}\n"
            f"📊 <b>إحصائياتنا:</b>\n"
            f"  📦 حسابات الكتالوج: <b>{stats['total']}</b>\n"
            f"  ✅ متاح الآن:       <b>{stats['available']}</b>\n"
            f"  🔴 تم بيعها:        <b>{stats['sold']}</b>\n\n"
            f"📞 تواصل مباشر: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return

    # ── Account Detail (user) ─────────────────────────────
    if data.startswith("detail_"):
        try:
            acc_id  = int(data.split("_", 1)[1])
            account = get_account(acc_id)
        except (ValueError, IndexError):
            account = None

        if not account:
            await query.edit_message_text(
                "❌ الحساب غير موجود أو تم حذفه.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        if account['status'] != 'available':
            await query.edit_message_text(
                f"⚠️ <b>هذا الحساب غير متاح حالياً</b>\n\n"
                f"الحالة: {_status_label(account['status'])}",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return

        text = _account_card(account)
        kb   = account_card_keyboard(acc_id)
        img  = account.get("image_path")

        try:
            if img and os.path.exists(img):
                await query.message.reply_photo(
                    photo=open(img, 'rb'),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb
                )
                await query.delete_message()
                return
        except Exception as e:
            logger.warning(f"Photo send failed: {e}")

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    # ── Buy (user) — show payment method selection ────────
    if data.startswith("buy_") and not data.startswith("buy_confirm"):
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

        stars = usd_to_stars(account['price'])
        year_line = f"  📅  سنة الإنشاء: <b>{account['creation_year']}</b>\n" if account.get('creation_year') else ""
        text = (
            f"🛒 <b>اختر طريقة الدفع</b>\n"
            f"{_divider()}\n\n"
            f"📦 الحساب: <b>{account['name']}</b>\n"
            f"{year_line}"
            f"💰 السعر:  <b>${account['price']:.2f}</b>\n\n"
            f"{_divider()}\n\n"
            f"⭐ <b>نجوم تيليجرام</b>  →  {stars} نجمة\n"
            f"   تسليم فوري <b>تلقائي</b> بعد الدفع ⚡\n\n"
            f"💎 <b>USDT TRC20</b>  →  ${account['price']:.2f}\n"
            f"   تسليم بعد تأكيد الأدمن\n\n"
            "👇 <i>اختر طريقة الدفع المناسبة لك</i>"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=payment_method_keyboard(acc_id, account['price'])
        )
        return

    # ── Pay with Stars ────────────────────────────────────
    if data.startswith("pay_stars_"):
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

        stars   = usd_to_stars(account['price'])
        payload = f"acc_{acc_id}_{user.id}"
        year_info = f" — {account['creation_year']}" if account.get('creation_year') else ""

        try:
            await context.bot.send_invoice(
                chat_id=user.id,
                title=f"🐦 {account['name']}{year_info}",
                description=(
                    f"حساب تويتر/X قديم وأصيل\n"
                    f"السعر: ${account['price']:.2f} • {stars} نجمة\n"
                    f"تسليم فوري بعد الدفع ⚡"
                ),
                payload=payload,
                currency="XTR",
                prices=[LabeledPrice(label=account['name'], amount=stars)],
            )
            await query.edit_message_text(
                f"⭐ <b>فاتورة النجوم أُرسلت!</b>\n\n"
                f"📦 الحساب: <b>{account['name']}</b>\n"
                f"💫 المبلغ: <b>{stars} نجمة</b>\n\n"
                "✅ بعد الدفع ستصلك بيانات الحساب <b>فوراً وتلقائياً</b> ⚡",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to send Stars invoice: {e}")
            await query.edit_message_text(
                f"❌ <b>فشل إرسال فاتورة النجوم</b>\n\n"
                f"تأكد أن البوت مفعّل للدفع بالنجوم من BotFather.\n\n"
                f"تواصل مع الأدمن: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>",
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
        return

    # ── Pay with USDT ─────────────────────────────────────
    if data.startswith("pay_usdt_"):
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

        buyer_username = user.username or "unknown"
        order_id       = create_order(acc_id, user.id, buyer_username)
        update_account(acc_id, status='reserved')

        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"💎 <b>طلب شراء بـ USDT جديد!</b>\n"
                    f"{_divider()}\n\n"
                    f"🆔 رقم الطلب: <code>#{order_id}</code>\n"
                    f"📦 الحساب:   <b>{account['name']}</b>\n"
                    f"💰 السعر:    <b>${account['price']:.2f} USDT</b>\n"
                    f"👤 المشتري:  @{buyer_username}\n"
                    f"🆔 ID:       <code>{user.id}</code>\n\n"
                    "⬇️ اضغط للتأكيد بعد التحقق من الدفع"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=admin_order_keyboard(order_id, acc_id)
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")

        success_text = (
            f"💎 <b>طلب USDT مسجّل!</b>\n"
            f"{_divider()}\n\n"
            f"🆔 رقم طلبك: <code>#{order_id}</code>\n"
            f"📦 الحساب:   <b>{account['name']}</b>\n\n"
            f"{_divider()}\n"
            f"📤 <b>أرسل المبلغ التالي:</b>\n\n"
            f"💵 <b>{account['price']:.2f} USDT</b>  (شبكة TRC20)\n\n"
            f"📋 <b>عنوان المحفظة:</b>\n"
            f"<code>{USDT_ADDRESS}</code>\n\n"
            f"{_divider()}\n"
            f"📸 <b>بعد الإرسال:</b>\n"
            f"أرسل صورة الإيصال لـ <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n"
            f"مع رقم طلبك: <code>#{order_id}</code>\n\n"
            "⚡ <i>تسليم بيانات الحساب فور تأكيد الأدمن</i>"
        )
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )
        return

    # ── Backward compat: confirm_buy redirects to payment selection ──
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

        stars = usd_to_stars(account['price'])
        year_line = f"  📅  سنة الإنشاء: <b>{account['creation_year']}</b>\n" if account.get('creation_year') else ""
        text = (
            f"🛒 <b>اختر طريقة الدفع</b>\n"
            f"{_divider()}\n\n"
            f"📦 الحساب: <b>{account['name']}</b>\n"
            f"{year_line}"
            f"💰 السعر:  <b>${account['price']:.2f}</b>\n\n"
            f"{_divider()}\n\n"
            f"⭐ <b>نجوم تيليجرام</b>  →  {stars} نجمة\n"
            f"   تسليم فوري <b>تلقائي</b> بعد الدفع ⚡\n\n"
            f"💎 <b>USDT TRC20</b>  →  ${account['price']:.2f}\n"
            f"   تسليم بعد تأكيد الأدمن\n\n"
            "👇 <i>اختر طريقة الدفع المناسبة لك</i>"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=payment_method_keyboard(acc_id, account['price'])
        )
        return

    # ═══════════════════════════════════════════════════════
    # ADMIN CALLBACKS
    # ═══════════════════════════════════════════════════════

    if not _is_admin(user.id):
        await query.answer("⛔ وصول مرفوض", show_alert=True)
        return

    # ── Admin stats ───────────────────────────────────────
    if data == "admin_stats":
        stats = get_stats()
        await query.edit_message_text(
            _build_stats_text(stats),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )
        return

    # ── Admin pending orders ──────────────────────────────
    if data == "admin_pending_orders":
        orders = get_pending_orders()
        if not orders:
            await query.edit_message_text(
                "📭 <b>لا توجد طلبات معلقة</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_keyboard()
            )
            return

        text = (
            f"📦 <b>الطلبات المعلقة</b>  ({len(orders)} طلب)\n"
            f"{_divider()}\n\n"
        )
        for o in orders[:10]:
            text += (
                f"🆔 طلب <code>#{o['id']}</code>\n"
                f"   📦 {o.get('account_name','—')}  💰 ${o.get('account_price',0):.2f}\n"
                f"   👤 @{o.get('buyer_username','—')}  ID: <code>{o['buyer_id']}</code>\n\n"
            )

        rows = [[InlineKeyboardButton(
            f"✅ تأكيد طلب #{o['id']}", callback_data=f"admin_confirm_order_{o['id']}"
        )] for o in orders[:5]]
        rows.append([InlineKeyboardButton("🔙  رجوع", callback_data="back_menu")])
        from telegram import InlineKeyboardMarkup
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    # ── Admin list accounts ───────────────────────────────
    if data.startswith("admin_list_"):
        page     = int(data.split("_")[-1])
        accounts = get_all_accounts_admin()
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        page    = max(0, min(page, total_pages - 1))
        chunk   = accounts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        header  = (
            f"📋 <b>جميع الحسابات</b>  ({len(accounts)} حساب)\n"
            f"{_divider()}\n"
            f"الصفحة {page+1} من {total_pages}"
        )
        await query.edit_message_text(
            header,
            parse_mode=ParseMode.HTML,
            reply_markup=accounts_page_keyboard(chunk, page, total_pages)
        )
        return

    # ── Admin view single account ─────────────────────────
    if data.startswith("admin_account_"):
        acc_id  = int(data.split("_")[-1])
        account = get_account(acc_id)
        if not account:
            await query.edit_message_text("❌ الحساب غير موجود", reply_markup=admin_keyboard())
            return
        text = _account_card(account, show_private=True)
        img  = account.get("image_path")
        try:
            if img and os.path.exists(img):
                await query.message.reply_photo(
                    photo=open(img, 'rb'),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=admin_account_keyboard(acc_id)
                )
                await query.delete_message()
                return
        except Exception as e:
            logger.warning(f"Photo error: {e}")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_account_keyboard(acc_id))
        return

    # ── Admin start add account ───────────────────────────
    if data == "admin_add_start":
        context.user_data.clear()
        context.user_data[STATE] = S_ADD_NAME
        context.user_data[DRAFT] = {}
        await query.edit_message_text(
            f"➕ <b>إضافة حساب جديد</b>\n"
            f"{_divider()}\n\n"
            "📝 أرسل <b>اسم الحساب</b> (مثال: @oldtwitter2010)\n\n"
            "<i>أرسل /cancel في أي وقت للإلغاء</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Admin edit account (show field selection) ─────────
    if data.startswith("admin_edit_"):
        acc_id = int(data.split("_")[-1])
        account = get_account(acc_id)
        if not account:
            await query.edit_message_text("❌ الحساب غير موجود")
            return
        await query.edit_message_text(
            f"✏️ <b>تعديل الحساب: {account['name']}</b>\n\n"
            "اختر الحقل الذي تريد تعديله:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_edit_field_keyboard(acc_id)
        )
        return

    # ── Admin set status directly ─────────────────────────
    if data.startswith("admin_setstatus_"):
        parts  = data.split("_")
        acc_id = int(parts[-2])
        status = parts[-1]
        update_account(acc_id, status=status)
        account = get_account(acc_id)
        await query.answer(f"✅ تم تغيير الحالة إلى {status}", show_alert=False)
        await query.edit_message_text(
            f"✏️ <b>تعديل الحساب: {account['name']}</b>\n\n"
            f"الحالة الجديدة: {_status_label(status)}\n\n"
            "اختر الحقل الذي تريد تعديله:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_edit_field_keyboard(acc_id)
        )
        return

    # ── Admin edit field (start input) ────────────────────
    if data.startswith("admin_editf_"):
        parts  = data.split("_")
        acc_id = int(parts[2])
        field  = "_".join(parts[3:])

        field_labels = {
            "name": "الاسم", "price": "السعر (رقم)", "creation_year": "سنة الإنشاء (رقم أو -)",
            "description": "الوصف", "email": "الإيميل", "password": "الباسورد",
            "followers": "عدد المتابعين (رقم)", "tweets_count": "عدد التغريدات (رقم)",
            "features": "المميزات الخاصة", "image": "صورة (أرسل الصورة)"
        }

        context.user_data[STATE]    = S_EDIT_PHOTO if field == "image" else S_EDIT_VALUE
        context.user_data[EDIT_ID]  = acc_id
        context.user_data[EDIT_FIELD] = field

        await query.edit_message_text(
            f"✏️ <b>تعديل: {field_labels.get(field, field)}</b>\n\n"
            f"{'أرسل الصورة الجديدة:' if field == 'image' else f'أرسل القيمة الجديدة لـ <b>{field_labels.get(field, field)}</b>:'}\n\n"
            "<i>أرسل /cancel للإلغاء</i>",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Admin delete confirm ──────────────────────────────
    if data.startswith("admin_del_confirm_"):
        acc_id  = int(data.split("_")[-1])
        account = get_account(acc_id)
        if not account:
            await query.edit_message_text("❌ الحساب غير موجود")
            return
        await query.edit_message_text(
            f"⚠️ <b>تأكيد الحذف</b>\n\n"
            f"هل تريد حذف الحساب:\n<b>{account['name']}</b>؟\n\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_delete_confirm_keyboard(acc_id)
        )
        return

    # ── Admin delete ──────────────────────────────────────
    if data.startswith("admin_del_"):
        acc_id = int(data.split("_")[-1])
        acc    = get_account(acc_id)
        name   = acc['name'] if acc else "—"
        delete_account(acc_id)
        await query.edit_message_text(
            f"🗑️ <b>تم حذف الحساب</b>\n\n"
            f"الحساب <b>{name}</b> تم حذفه بنجاح.",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )
        return

    # ── Admin confirm order (USDT manual) ─────────────────
    if data.startswith("admin_confirm_order_"):
        order_id = int(data.split("_")[-1])
        order    = get_order(order_id)

        if not order:
            await query.edit_message_text("❌ الطلب غير موجود.")
            return
        if order['status'] in ('completed', 'cancelled'):
            await query.edit_message_text(
                f"⚠️ الطلب #{order_id} سبق معالجته (الحالة: {order['status']})"
            )
            return

        update_order(order_id, 'completed')
        update_account(order['account_id'], status='sold')

        delivered = await _deliver_account(context.bot, order['buyer_id'], order)

        admin_confirm = (
            f"✅ <b>تم تأكيد الطلب #{order_id}</b>\n\n"
            f"📦 {order.get('account_name','—')}\n"
            f"👤 @{order.get('buyer_username','—')}\n"
            f"{'📬 تم إرسال بيانات الدخول للمشتري ⚡' if delivered else '⚠️ فشل إرسال البيانات للمشتري — أرسلها يدوياً'}"
        )
        await query.edit_message_text(admin_confirm, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())
        return

    # ── Admin reject order ────────────────────────────────
    if data.startswith("admin_reject_order_"):
        order_id = int(data.split("_")[-1])
        order    = get_order(order_id)
        if not order:
            await query.edit_message_text("❌ الطلب غير موجود.")
            return

        update_order(order_id, 'cancelled')
        update_account(order['account_id'], status='available')

        try:
            await context.bot.send_message(
                chat_id=order['buyer_id'],
                text=(
                    f"❌ <b>تم إلغاء طلبك #{order_id}</b>\n\n"
                    f"للاستفسار: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Could not notify buyer of rejection: {e}")

        await query.edit_message_text(
            f"❌ <b>تم رفض الطلب #{order_id}</b> وإعادة الحساب للمتجر.",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )
        return

    # ── Noop ──────────────────────────────────────────────
    if data == "noop":
        await query.answer("افتح المتجر عبر رابط خارجي", show_alert=True)
        return

    logger.debug(f"Unhandled callback: {data}")


# ── InlineKeyboardButton import fix ───────────────────────
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
