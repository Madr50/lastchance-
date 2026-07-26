# bot_handlers.py — Complete Telegram bot handlers
import logging
import os
import html as _html
from telegram import Update, InputMediaPhoto, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID, ADMIN_USERNAME, SHOP_NAME, USDT_ADDRESS
from database import (
    register_user, get_user, get_user_by_ref, get_all_users,
    get_all_accounts, get_account, get_all_accounts_admin,
    create_order, update_account, delete_account,
    get_stats, get_all_orders, get_pending_orders,
    get_order, update_order, add_account,
    get_active_competitions, get_all_competitions, get_competition,
    create_competition, update_competition, end_competition, delete_competition,
    get_competition_entry, get_competition_leaderboard,
    join_competition, get_competition_participants_count,
)
from bot_keyboards import (
    main_menu_keyboard, admin_keyboard,
    account_card_keyboard, back_to_menu_keyboard, back_to_admin_keyboard,
    payment_method_keyboard, usdt_payment_keyboard,
    admin_account_keyboard, admin_delete_confirm_keyboard,
    admin_edit_field_keyboard, admin_order_keyboard,
    accounts_page_keyboard, user_accounts_page_keyboard,
    competitions_keyboard, competition_detail_keyboard, competition_join_keyboard,
    admin_competitions_keyboard, admin_competition_detail_keyboard,
    invite_keyboard,
    admin_comp_delete_confirm_keyboard, admin_comp_edit_field_keyboard,
    usd_to_stars
)

logger = logging.getLogger(__name__)

# ── State machine keys ──────────────────────────────────────
STATE      = "bot_state"
DRAFT      = "bot_draft"
EDIT_ID    = "edit_acc_id"
EDIT_FIELD = "edit_field"

# User states
S_IDLE            = "idle"
S_ADD_NAME        = "add_name"
S_ADD_YEAR        = "add_year"
S_ADD_PRICE       = "add_price"
S_ADD_EMAIL       = "add_email"
S_ADD_PASSWORD    = "add_password"
S_ADD_FOLLOWERS   = "add_followers"
S_ADD_TWEETS      = "add_tweets"
S_ADD_FEATURES    = "add_features"
S_ADD_DESC        = "add_desc"
S_ADD_PHOTO       = "add_photo"
S_EDIT_VALUE      = "edit_value"
S_EDIT_PHOTO      = "edit_photo"
# Competition states
S_COMP_TITLE      = "comp_title"
S_COMP_DESC       = "comp_desc"
S_COMP_INVITES    = "comp_invites"
S_COMP_PHOTO      = "comp_photo"
S_COMP_EDIT_VALUE = "comp_edit_value"
S_COMP_EDIT_PHOTO = "comp_edit_photo"

PAGE_SIZE = 6

# ── Helpers ─────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def _divider() -> str:
    return "━━━━━━━━━━━━━━━━━━━━━━━━"


def _fmt_num(n) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _status_label(status: str) -> str:
    return {
        "available": "✅ متاح للبيع",
        "sold":      "🔴 تم البيع",
        "reserved":  "⏳ محجوز",
    }.get(status, status)


def _account_card(acc: dict, show_private: bool = False) -> str:
    name = _html.escape(acc.get('name') or '')
    desc = _html.escape((acc.get('description') or '')[:350])
    feat = _html.escape(acc.get('features') or '')
    year  = f"  📅  سنة الإنشاء: <b>{acc['creation_year']}</b>\n" if acc.get('creation_year') else ""
    flw   = _fmt_num(acc.get('followers') or 0)
    twts  = _fmt_num(acc.get('tweets_count') or 0)
    feat_line = f"\n⭐ <b>المميزات:</b> {feat}\n" if feat else ""
    stats_line = ""
    if int(acc.get('followers') or 0) or int(acc.get('tweets_count') or 0):
        stats_line = f"  👥  متابعون: <b>{flw}</b>   🐦  تغريدات: <b>{twts}</b>\n"

    private = ""
    if show_private:
        email = _html.escape(acc.get('email') or '—')
        pw    = _html.escape(acc.get('password') or '—')
        private = (
            f"\n{_divider()}\n"
            f"🔐 <b>بيانات الدخول (خاص — أدمن فقط):</b>\n"
            f"  📧 الإيميل:  <code>{email}</code>\n"
            f"  🔑 الباسورد: <code>{pw}</code>\n"
        )

    return (
        f"🐦 <b>{name}</b>\n"
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
        f"  📦  إجمالي الحسابات: <b>{stats['total_accounts']}</b>\n"
        f"  ✅  متاح: <b>{stats['available']}</b>\n"
        f"  🔴  مباع: <b>{stats['sold']}</b>\n"
        f"  💰  الإيرادات: <b>${stats['revenue']:.2f}</b>\n"
        f"  📋  الطلبات الكل: <b>{stats['total_orders']}</b>\n"
        f"  ⏳  طلبات معلقة: <b>{stats['pending_orders']}</b>\n"
        f"  👥  المستخدمون: <b>{stats['total_users']}</b>\n"
        f"  🏆  مسابقات نشطة: <b>{stats['active_competitions']}</b>"
    )


def _build_competition_card(comp: dict, user_id: int = None) -> str:
    title = _html.escape(comp.get('title') or '')
    desc  = _html.escape(comp.get('description') or '')
    req   = comp.get('required_invites', 15)
    participants = get_competition_participants_count(comp['id'])

    text = (
        f"🏆 <b>{title}</b>\n"
        f"{_divider()}\n"
        f"📝 {desc}\n\n"
        f"🎯 الهدف: دعوة <b>{req} شخص</b> للبوت\n"
        f"👥 المشاركون: <b>{participants}</b>\n"
    )

    if user_id:
        entry = get_competition_entry(comp['id'], user_id)
        if entry:
            count   = entry['invite_count']
            percent = min(int(count / req * 100), 100)
            filled  = int(count / req * 10)
            bar     = "🟦" * filled + "⬜" * (10 - filled)
            text += (
                f"\n{_divider()}\n"
                f"📊 <b>تقدمك:</b> {count}/{req}\n"
                f"{bar} {percent}%\n"
            )
            if count >= req:
                text += "\n🎉 <b>لقد أكملت الهدف! انتظر إعلان الفائز.</b>\n"
        else:
            text += f"\n<i>لم تنضم بعد — اضغط انضم للمسابقة</i>\n"

    return text


async def _safe_edit(query, text, keyboard=None, parse_mode=ParseMode.HTML, photo_url=None):
    """Edit the message in place, handling both text and photo messages."""
    try:
        if photo_url and query.message.photo:
            await query.message.edit_caption(
                caption=text, parse_mode=parse_mode, reply_markup=keyboard
            )
        elif photo_url:
            await query.message.edit_text(text, parse_mode=parse_mode, reply_markup=keyboard)
        else:
            if query.message.photo:
                await query.message.edit_caption(
                    caption=text, parse_mode=parse_mode, reply_markup=keyboard
                )
            else:
                await query.message.edit_text(
                    text, parse_mode=parse_mode, reply_markup=keyboard
                )
    except Exception as e:
        logger.debug(f"edit failed: {e}")
        await query.answer()


async def _safe_reply(query, text, parse_mode=ParseMode.HTML, reply_markup=None):
    try:
        await query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"reply_text failed: {e}")


async def _deliver_account(bot, buyer_id: int, order: dict) -> bool:
    """Send account credentials to buyer."""
    try:
        acc = get_account(order['account_id'])
        if not acc:
            return False
        email    = _html.escape(acc.get('email') or '—')
        password = _html.escape(acc.get('password') or '—')
        features = _html.escape(acc.get('features') or '')
        msg = (
            f"🎉 <b>مبروك! تم تأكيد دفعك</b>\n\n"
            f"📦 الحساب: <b>{_html.escape(acc['name'])}</b>\n\n"
            f"{_divider()}\n"
            f"🔐 <b>بيانات دخول حسابك:</b>\n\n"
            f"  📧 الإيميل:  <code>{email}</code>\n"
            f"  🔑 الباسورد: <code>{password}</code>\n"
        )
        if features:
            msg += f"\n⭐ المميزات: {features}\n"
        msg += (
            f"\n{_divider()}\n"
            f"📞 للدعم: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n\n"
            "✨ <i>شكراً لثقتك بنا!</i>"
        )
        await bot.send_message(chat_id=buyer_id, text=msg, parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        logger.error(f"Deliver failed: {e}")
        return False


def _get_invite_link(user_id: int) -> str:
    """Get the personal invite link for a user."""
    bot_username = os.environ.get("BOT_USERNAME", "")
    user = get_user(user_id)
    if not user:
        return ""
    code = user.get("ref_code", "")
    if bot_username:
        return f"https://t.me/{bot_username}?start=ref_{code}"
    return f"رمز الدعوة: <code>ref_{code}</code>"


def _get_competition_invite_link(user_id: int, comp_id: int) -> str:
    """Get personal competition invite link (same link, competition joins automatically)."""
    bot_username = os.environ.get("BOT_USERNAME", "")
    user = get_user(user_id)
    if not user:
        return ""
    code = user.get("ref_code", "")
    if bot_username:
        return f"https://t.me/{bot_username}?start=ref_{code}_comp{comp_id}"
    return f"رمز الدعوة: <code>ref_{code}_comp{comp_id}</code>"


# ══════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args or []
    arg  = args[0] if args else ""

    invited_by = None
    comp_id    = None

    # Parse ref code: "ref_XXXX" or "ref_XXXX_compY"
    if arg.startswith("ref_"):
        parts = arg[4:].split("_comp")
        ref_code = parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            comp_id = int(parts[1])

        inviter = get_user_by_ref(ref_code)
        if inviter and inviter['telegram_id'] != user.id:
            invited_by = inviter['telegram_id']

    # Register user (credits inviter if applicable)
    db_user = register_user(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        invited_by=invited_by
    )

    # Join competition if referred via competition link
    if comp_id:
        comp = get_competition(comp_id)
        if comp and comp['status'] == 'active':
            join_competition(comp_id, user.id)

    welcome = (
        f"👋 <b>أهلاً بك في {_html.escape(SHOP_NAME)}!</b>\n\n"
        f"نبيع حسابات تويتر X قديمة الإنشاء بأفضل الأسعار 🐦\n\n"
        f"🔐 حسابات أصلية مضمونة\n"
        f"⚡ تسليم فوري بعد الدفع\n"
        f"💎 أسعار تنافسية\n\n"
        f"اختر من القائمة أدناه 👇"
    )
    await update.message.reply_text(
        welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"📖 <b>طريقة الاستخدام</b>\n\n"
        f"/start — الرئيسية\n"
        f"/shop — تصفح الحسابات\n"
        f"/myinvites — رابط الدعوة الخاص بك\n"
        f"/competitions — المسابقات الحالية\n"
        f"/cancel — إلغاء العملية الحالية\n"
    )
    if _is_admin(update.effective_user.id):
        text += f"\n👮 <b>أوامر الأدمن:</b>\n/admin — لوحة التحكم"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    accounts = get_all_accounts(status="available")
    if not accounts:
        await update.message.reply_text(
            "😔 <b>لا توجد حسابات متاحة حالياً</b>",
            parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return
    await _send_accounts_page(update.message, accounts, 0)


async def cmd_myinvites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user    = update.effective_user
    db_user = register_user(user.id, user.username or "", user.first_name or "")
    link    = _get_invite_link(user.id)
    text = (
        f"🎁 <b>رابط الدعوة الخاص بك</b>\n"
        f"{_divider()}\n\n"
        f"إجمالي من دعوتهم: <b>{db_user.get('total_invites', 0)}</b> شخص\n\n"
        f"🔗 رابطك الشخصي:\n"
        f"<code>{link}</code>\n\n"
        f"<i>شارك هذا الرابط — كل من يدخل عبره يُحسب في رصيدك!</i>"
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=invite_keyboard(link)
    )


async def cmd_competitions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    comps = get_active_competitions()
    if not comps:
        await update.message.reply_text(
            "🏆 <b>لا توجد مسابقات نشطة حالياً</b>\n\nتابعنا للإعلانات القادمة!",
            parse_mode=ParseMode.HTML, reply_markup=back_to_menu_keyboard()
        )
        return
    await update.message.reply_text(
        "🏆 <b>المسابقات الحالية</b>\n\nاختر مسابقة للمشاركة 👇",
        parse_mode=ParseMode.HTML, reply_markup=competitions_keyboard(comps)
    )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text(
            "⛔ <b>وصول مرفوض</b>", parse_mode=ParseMode.HTML
        )
        return
    context.user_data.clear()
    stats = get_stats()
    await update.message.reply_text(
        _build_stats_text(stats), parse_mode=ParseMode.HTML, reply_markup=admin_keyboard()
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    kb = admin_keyboard() if _is_admin(update.effective_user.id) else main_menu_keyboard()
    await update.message.reply_text("❌ تم الإلغاء", parse_mode=ParseMode.HTML, reply_markup=kb)


# ══════════════════════════════════════════════
#  HELPERS — SEND PAGE
# ══════════════════════════════════════════════

async def _send_accounts_page(target, accounts, page: int) -> None:
    total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = max(0, min(page, total_pages - 1))
    chunk       = accounts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    text = (
        f"📋 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\n"
        f"الصفحة {page+1} من {total_pages}\n"
        f"{_divider()}\n"
        f"اختر حساباً لعرض تفاصيله 👇"
    )
    await target.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=user_accounts_page_keyboard(chunk, page, total_pages)
    )


# ══════════════════════════════════════════════
#  BUTTON HANDLER
# ══════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = update.effective_user

    # ── Navigation ──────────────────────────────────────────
    if data == "back_menu":
        await _safe_edit(query, f"🏠 <b>القائمة الرئيسية</b>\n\nاختر من الأسفل 👇",
                         main_menu_keyboard())
        return

    if data == "back_admin":
        if not _is_admin(user.id):
            return
        stats = get_stats()
        await _safe_edit(query, _build_stats_text(stats), admin_keyboard())
        return

    # ── My invites ──────────────────────────────────────────
    if data == "my_invites":
        db_user = register_user(user.id, user.username or "", user.first_name or "")
        link    = _get_invite_link(user.id)
        text = (
            f"🎁 <b>رابط الدعوة الخاص بك</b>\n"
            f"{_divider()}\n\n"
            f"إجمالي الدعوات: <b>{db_user.get('total_invites', 0)}</b>\n\n"
            f"🔗 رابطك الشخصي:\n"
            f"<code>{link}</code>\n\n"
            f"<i>كل شخص يدخل عبر رابطك يُحسب في رصيدك!</i>"
        )
        await _safe_edit(query, text, invite_keyboard(link))
        return

    # ── Browse accounts (web app fallback) ─────────────────
    if data == "browse_accounts":
        accounts = get_all_accounts(status="available")
        if not accounts:
            await _safe_edit(query, "😔 <b>لا توجد حسابات متاحة حالياً</b>", back_to_menu_keyboard())
            return
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        chunk       = accounts[:PAGE_SIZE]
        await _safe_edit(
            query,
            f"📋 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\n{_divider()}\nاختر حساباً 👇",
            user_accounts_page_keyboard(chunk, 0, total_pages)
        )
        return

    # ── List accounts (user) ────────────────────────────────
    if data == "list_accounts":
        accounts = get_all_accounts(status="available")
        if not accounts:
            await _safe_edit(query, "😔 <b>لا توجد حسابات متاحة حالياً</b>", back_to_menu_keyboard())
            return
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        chunk       = accounts[:PAGE_SIZE]
        await _safe_edit(
            query,
            f"📋 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\nالصفحة 1 من {total_pages}\n{_divider()}\nاختر حساباً 👇",
            user_accounts_page_keyboard(chunk, 0, total_pages)
        )
        return

    # ── Account page navigation ─────────────────────────────
    if data.startswith("page_accounts_"):
        page     = int(data.split("_")[-1])
        accounts = get_all_accounts(status="available")
        total_pages = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
        page     = max(0, min(page, total_pages - 1))
        chunk    = accounts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        await _safe_edit(
            query,
            f"📋 <b>الحسابات المتاحة</b>  ({len(accounts)} حساب)\nالصفحة {page+1} من {total_pages}\n{_divider()}\nاختر حساباً 👇",
            user_accounts_page_keyboard(chunk, page, total_pages)
        )
        return

    # ── Account detail (user) ───────────────────────────────
    if data.startswith("detail_"):
        parts  = data.split("_")
        acc_id = int(parts[1])
        page   = int(parts[2]) if len(parts) > 2 else 0
        acc    = get_account(acc_id)
        if not acc:
            await query.answer("❌ الحساب غير موجود", show_alert=True)
            return

        card = _account_card(acc)
        kb   = account_card_keyboard(acc_id, page)

        if acc.get("image_path"):
            img = acc["image_path"]
            try:
                if query.message.photo:
                    await query.message.edit_caption(caption=card, parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await query.message.delete()
                    with open(img, "rb") as f:
                        await query.message.reply_photo(photo=f, caption=card, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                await _safe_edit(query, card, kb)
        else:
            await _safe_edit(query, card, kb)
        return

    # ── Buy ─────────────────────────────────────────────────
    if data.startswith("buy_"):
        acc_id = int(data.split("_")[1])
        acc    = get_account(acc_id)
        if not acc or acc['status'] != 'available':
            await query.answer("❌ هذا الحساب لم يعد متاحاً", show_alert=True)
            return
        text = (
            f"💳 <b>اختر طريقة الدفع</b>\n"
            f"{_divider()}\n"
            f"📦 {_html.escape(acc['name'])}\n"
            f"💰 السعر: <b>${acc['price']:.2f}</b>\n\n"
            f"اختر طريقة الدفع:"
        )
        await _safe_edit(query, text, payment_method_keyboard(acc_id, acc['price']))
        return

    # ── Pay with Stars ──────────────────────────────────────
    if data.startswith("pay_stars_"):
        acc_id = int(data.split("_")[-1])
        acc    = get_account(acc_id)
        if not acc or acc['status'] != 'available':
            await query.answer("❌ الحساب لم يعد متاحاً", show_alert=True)
            return
        stars = usd_to_stars(acc['price'])
        try:
            await context.bot.send_invoice(
                chat_id=user.id,
                title=f"🐦 {acc['name']}",
                description=f"حساب تويتر قديم • ${acc['price']:.2f}",
                payload=f"account_{acc['id']}",
                currency="XTR",
                prices=[LabeledPrice(label=acc['name'], amount=stars)],
            )
            update_account(acc_id, status='reserved')
            await query.answer("✅ تم إرسال فاتورة النجوم")
        except Exception as e:
            logger.error(f"Stars invoice error: {e}")
            await query.answer("❌ خطأ في إنشاء الفاتورة", show_alert=True)
        return

    # ── Pay with USDT ───────────────────────────────────────
    if data.startswith("pay_usdt_"):
        acc_id = int(data.split("_")[-1])
        acc    = get_account(acc_id)
        if not acc or acc['status'] != 'available':
            await query.answer("❌ الحساب لم يعد متاحاً", show_alert=True)
            return

        order_id = create_order(acc_id, user.id, user.username or "")
        update_account(acc_id, status='reserved')

        text = (
            f"💎 <b>الدفع عبر USDT (TRC20)</b>\n"
            f"{_divider()}\n\n"
            f"📦 الحساب: <b>{_html.escape(acc['name'])}</b>\n"
            f"💰 المبلغ: <b>${acc['price']:.2f}</b>\n\n"
            f"عنوان المحفظة:\n"
            f"<code>{USDT_ADDRESS}</code>\n\n"
            f"⚠️ أرسل المبلغ بالضبط ثم اضغط الزر أدناه لإشعار الأدمن."
        )
        await _safe_edit(query, text, usdt_payment_keyboard(order_id, USDT_ADDRESS))
        return

    # ── USDT sent notification ──────────────────────────────
    if data.startswith("usdt_sent_"):
        order_id = int(data.split("_")[-1])
        order    = get_order(order_id)
        if not order:
            return
        try:
            kb = admin_order_keyboard(order_id)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"💎 <b>طلب USDT جديد #{order_id}</b>\n"
                    f"{_divider()}\n"
                    f"📦 الحساب: {_html.escape(order.get('account_name','—'))}\n"
                    f"👤 المشتري: @{order.get('buyer_username','—')}\n"
                    f"💰 السعر: ${order.get('price', 0):.2f}\n\n"
                    f"تحقق من الدفع وأكده."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        except Exception as e:
            logger.warning(f"Admin notify failed: {e}")
        await _safe_edit(
            query,
            "⏳ <b>تم إرسال طلبك للأدمن</b>\n\nسيتم مراجعة دفعتك وتسليم الحساب قريباً.",
            back_to_menu_keyboard()
        )
        return

    # ── How to buy ──────────────────────────────────────────
    if data == "how_to_buy":
        text = (
            f"📖 <b>طريقة الشراء</b>\n"
            f"{_divider()}\n\n"
            f"1️⃣ تصفح الحسابات المتاحة\n"
            f"2️⃣ اختر الحساب المناسب\n"
            f"3️⃣ اضغط «اشتري هذا الحساب»\n"
            f"4️⃣ اختر طريقة الدفع:\n"
            f"   ⭐ نجوم تيليغرام\n"
            f"   💎 USDT (TRC20)\n"
            f"5️⃣ استلم بيانات الحساب فوراً!\n\n"
            f"للدعم: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
        )
        await _safe_edit(query, text, back_to_menu_keyboard())
        return

    # ── About ───────────────────────────────────────────────
    if data == "about":
        text = (
            f"ℹ️ <b>عن {_html.escape(SHOP_NAME)}</b>\n"
            f"{_divider()}\n\n"
            f"🏪 متجر متخصص ببيع حسابات تويتر X قديمة الإنشاء\n"
            f"🔐 جميع الحسابات مضمونة وأصلية\n"
            f"⚡ تسليم فوري وآمن\n"
            f"💎 أسعار تنافسية\n\n"
            f"📞 للتواصل: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
        )
        await _safe_edit(query, text, back_to_menu_keyboard())
        return

    # ── Pricing info ────────────────────────────────────────
    if data == "pricing_info":
        accounts = get_all_accounts(status="available")
        if not accounts:
            await _safe_edit(query, "😔 لا توجد حسابات متاحة.", back_to_menu_keyboard())
            return
        prices = sorted(set(a['price'] for a in accounts))
        lines  = "\n".join(f"  • ${p:.2f}" for p in prices[:10])
        await _safe_edit(
            query,
            f"💰 <b>نطاق الأسعار</b>\n{_divider()}\n\n{lines}\n\nاستخدم المتجر لرؤية جميع التفاصيل.",
            back_to_menu_keyboard()
        )
        return

    # ═════════════════════════════════════════
    #  COMPETITIONS (user)
    # ═════════════════════════════════════════

    if data == "competitions_list":
        comps = get_active_competitions()
        if not comps:
            await _safe_edit(
                query, "🏆 <b>لا توجد مسابقات نشطة حالياً</b>", back_to_menu_keyboard()
            )
            return
        await _safe_edit(
            query,
            "🏆 <b>المسابقات الحالية</b>\nاختر مسابقة 👇",
            competitions_keyboard(comps)
        )
        return

    if data.startswith("competition_"):
        comp_id = int(data.split("_")[1])
        comp    = get_competition(comp_id)
        if not comp or comp['status'] != 'active':
            await query.answer("❌ المسابقة غير موجودة أو انتهت", show_alert=True)
            return
        db_user = register_user(user.id, user.username or "", user.first_name or "")
        entry   = get_competition_entry(comp_id, user.id)
        text    = _build_competition_card(comp, user.id)
        if entry:
            kb = competition_detail_keyboard(comp_id)
        else:
            kb = competition_join_keyboard(comp_id)

        if comp.get("image_path"):
            try:
                if query.message.photo:
                    await query.message.edit_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await query.message.delete()
                    with open(comp["image_path"], "rb") as f:
                        await query.message.reply_photo(photo=f, caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
                return
            except Exception:
                pass
        await _safe_edit(query, text, kb)
        return

    if data.startswith("comp_join_"):
        comp_id = int(data.split("_")[-1])
        comp    = get_competition(comp_id)
        if not comp or comp['status'] != 'active':
            await query.answer("❌ المسابقة غير نشطة", show_alert=True)
            return
        join_competition(comp_id, user.id)
        text = _build_competition_card(comp, user.id)
        await _safe_edit(query, text, competition_detail_keyboard(comp_id))
        return

    if data.startswith("comp_mylink_"):
        comp_id = int(data.split("_")[-1])
        comp    = get_competition(comp_id)
        db_user = register_user(user.id, user.username or "", user.first_name or "")
        link    = _get_competition_invite_link(user.id, comp_id)
        entry   = get_competition_entry(comp_id, user.id)
        count   = entry['invite_count'] if entry else 0
        req     = comp.get('required_invites', 15) if comp else 15

        text = (
            f"🎁 <b>رابط دعوتك في المسابقة</b>\n"
            f"{_divider()}\n\n"
            f"🏆 {_html.escape(comp['title'] if comp else '')}\n\n"
            f"دعوتك حتى الآن: <b>{count}/{req}</b>\n\n"
            f"🔗 رابطك الخاص:\n"
            f"<code>{link}</code>\n\n"
            f"<i>شارك الرابط — كل شخص يدخل عبره يُحسب في المسابقة!</i>"
        )
        await _safe_edit(query, text, competition_detail_keyboard(comp_id))
        return

    if data.startswith("comp_leaderboard_"):
        comp_id  = int(data.split("_")[-1])
        comp     = get_competition(comp_id)
        leaders  = get_competition_leaderboard(comp_id, 10)
        req      = comp.get('required_invites', 15) if comp else 15
        lines    = []
        medals   = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(leaders):
            medal    = medals[i] if i < 3 else f"{i+1}."
            name     = _html.escape(row.get('first_name') or row.get('username') or f"User{row['user_id']}")
            count    = row['invite_count']
            bar_fill = min(int(count / req * 5), 5)
            bar      = "🟦" * bar_fill + "⬜" * (5 - bar_fill)
            lines.append(f"{medal} <b>{name}</b> — {count}/{req} {bar}")

        text = (
            f"🏅 <b>المتصدرون</b>\n"
            f"🏆 {_html.escape(comp['title'] if comp else '')}\n"
            f"{_divider()}\n\n"
            + ("\n".join(lines) if lines else "<i>لا يوجد مشاركون بعد</i>")
        )
        await _safe_edit(query, text, competition_detail_keyboard(comp_id))
        return

    # ═════════════════════════════════════════
    #  ADMIN — ACCOUNTS
    # ═════════════════════════════════════════

    if not _is_admin(user.id):
        # non-admin, ignore admin callbacks
        pass
    else:

        if data == "admin_stats":
            stats = get_stats()
            await _safe_edit(query, _build_stats_text(stats), admin_keyboard())
            return

        if data.startswith("admin_list_"):
            page     = int(data.split("_")[-1])
            accounts = get_all_accounts_admin()
            total_p  = max(1, (len(accounts) + PAGE_SIZE - 1) // PAGE_SIZE)
            page     = max(0, min(page, total_p - 1))
            chunk    = accounts[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
            await _safe_edit(
                query,
                f"📋 <b>جميع الحسابات</b>  ({len(accounts)})\nصفحة {page+1}/{total_p}",
                accounts_page_keyboard(chunk, page, total_p)
            )
            return

        if data.startswith("admin_account_"):
            acc_id = int(data.split("_")[-1])
            acc    = get_account(acc_id)
            if not acc:
                await query.answer("❌ لم يُعثر على الحساب")
                return
            card = _account_card(acc, show_private=True)
            await _safe_edit(query, card, admin_account_keyboard(acc_id))
            return

        if data.startswith("admin_status_"):
            parts  = data.split("_")
            acc_id = int(parts[2])
            status = parts[3]
            update_account(acc_id, status=status)
            acc  = get_account(acc_id)
            card = _account_card(acc, show_private=True)
            await _safe_edit(query, f"✅ تم تغيير الحالة إلى «{status}»\n\n{card}",
                             admin_account_keyboard(acc_id))
            return

        if data.startswith("admin_del_confirm_"):
            acc_id = int(data.split("_")[-1])
            await _safe_edit(
                query,
                "🗑️ <b>تأكيد الحذف</b>\nهل تريد حذف هذا الحساب نهائياً؟",
                admin_delete_confirm_keyboard(acc_id)
            )
            return

        if data.startswith("admin_del_"):
            acc_id = int(data.split("_")[-1])
            delete_account(acc_id)
            await _safe_edit(query, "✅ تم حذف الحساب.", admin_keyboard())
            return

        if data.startswith("admin_edit_"):
            acc_id = int(data.split("_")[-1])
            await _safe_edit(
                query,
                "✏️ <b>تعديل الحساب</b>\nاختر الحقل الذي تريد تعديله:",
                admin_edit_field_keyboard(acc_id)
            )
            return

        if data.startswith("admin_editfield_"):
            parts  = data.split("_")
            acc_id = int(parts[2])
            field  = parts[3]
            context.user_data[STATE]     = S_EDIT_PHOTO if field == "photo" else S_EDIT_VALUE
            context.user_data[EDIT_ID]   = acc_id
            context.user_data[EDIT_FIELD] = field
            if field == "photo":
                await _safe_edit(query, "📸 <b>أرسل الصورة الجديدة للحساب:</b>", back_to_admin_keyboard())
            else:
                labels = {
                    "name": "الاسم", "description": "الوصف", "price": "السعر",
                    "creation_year": "سنة الإنشاء", "email": "الإيميل",
                    "password": "الباسورد", "followers": "عدد المتابعين",
                    "tweets_count": "عدد التغريدات", "features": "المميزات",
                }
                await _safe_edit(
                    query,
                    f"✏️ أدخل القيمة الجديدة لـ «{labels.get(field, field)}»:",
                    back_to_admin_keyboard()
                )
            return

        # ── Add account ──────────────────────────────────────────
        if data == "admin_add_start":
            context.user_data.clear()
            context.user_data[STATE] = S_ADD_NAME
            context.user_data[DRAFT] = {}
            await _safe_edit(
                query,
                "➕ <b>إضافة حساب جديد</b>\n\n📝 <b>اسم الحساب:</b>\nأدخل اسم الحساب (مثال: @TwitterHandle)",
                back_to_admin_keyboard()
            )
            return

        # ── Pending orders ───────────────────────────────────────
        if data == "admin_pending_orders":
            orders = get_pending_orders()
            if not orders:
                await _safe_edit(query, "📦 <b>لا توجد طلبات معلقة</b>", admin_keyboard())
                return
            rows = []
            for o in orders[:10]:
                rows.append([
                    InlineKeyboardButton(
                        f"#{o['id']} — {o.get('account_name','—')} — @{o.get('buyer_username','—')}",
                        callback_data=f"admin_order_{o['id']}"
                    )
                ])
            rows.append([InlineKeyboardButton("🔙  لوحة التحكم", callback_data="back_admin")])
            await _safe_edit(
                query,
                f"📦 <b>الطلبات المعلقة</b>  ({len(orders)})",
                InlineKeyboardMarkup(rows)
            )
            return

        if data.startswith("admin_order_"):
            order_id = int(data.split("_")[-1])
            order    = get_order(order_id)
            if not order:
                await query.answer("❌ الطلب غير موجود")
                return
            text = (
                f"📦 <b>الطلب #{order_id}</b>\n"
                f"{_divider()}\n"
                f"الحساب: {_html.escape(order.get('account_name','—'))}\n"
                f"المشتري: @{order.get('buyer_username','—')}\n"
                f"السعر: ${order.get('price', 0):.2f}\n"
                f"الحالة: {order.get('status','—')}"
            )
            await _safe_edit(query, text, admin_order_keyboard(order_id))
            return

        if data.startswith("admin_confirm_order_"):
            order_id = int(data.split("_")[-1])
            order    = get_order(order_id)
            if not order:
                await query.answer("❌ الطلب غير موجود")
                return
            update_order(order_id, 'completed')
            update_account(order['account_id'], status='sold')
            delivered = await _deliver_account(context.bot, order['buyer_id'], order)
            await _safe_edit(
                query,
                f"✅ <b>تم تأكيد الطلب #{order_id}</b>\n{'📬 تم إرسال البيانات للمشتري' if delivered else '⚠️ فشل الإرسال — أرسل البيانات يدوياً'}",
                admin_keyboard()
            )
            return

        if data.startswith("admin_reject_order_"):
            order_id = int(data.split("_")[-1])
            order    = get_order(order_id)
            if not order:
                await query.answer("❌ الطلب غير موجود")
                return
            update_order(order_id, 'cancelled')
            update_account(order['account_id'], status='available')
            try:
                await context.bot.send_message(
                    chat_id=order['buyer_id'],
                    text=f"❌ <b>تم إلغاء طلبك #{order_id}</b>\nللاستفسار: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            await _safe_edit(query, f"❌ <b>تم رفض الطلب #{order_id}</b>", admin_keyboard())
            return

        # ── Admin users list ─────────────────────────────────────
        if data == "admin_users":
            users = get_all_users()[:20]
            lines = []
            for u in users:
                name = _html.escape(u.get('first_name') or u.get('username') or str(u['telegram_id']))
                lines.append(f"👤 {name} — {u.get('total_invites',0)} دعوة")
            text = (
                f"👥 <b>المستخدمون</b> ({len(get_all_users())} إجمالاً)\n"
                f"{_divider()}\n\n" + "\n".join(lines or ["<i>لا يوجد مستخدمون</i>"])
            )
            await _safe_edit(query, text, admin_keyboard())
            return

        # ═════════════════════════════════════════
        #  ADMIN — COMPETITIONS
        # ═════════════════════════════════════════

        if data == "admin_competitions":
            comps = get_all_competitions()
            await _safe_edit(
                query,
                f"🏆 <b>المسابقات</b>  ({len(comps)})",
                admin_competitions_keyboard(comps)
            )
            return

        if data.startswith("admin_comp_"):
            tail = data[len("admin_comp_"):]

            # Add competition
            if tail == "add":
                context.user_data.clear()
                context.user_data[STATE] = S_COMP_TITLE
                context.user_data[DRAFT] = {}
                await _safe_edit(
                    query,
                    "🏆 <b>إضافة مسابقة جديدة</b>\n\n📝 أدخل عنوان المسابقة:",
                    back_to_admin_keyboard()
                )
                return

            # Delete confirmed
            if tail.startswith("del_confirm_"):
                comp_id = int(tail.split("_")[-1])
                await _safe_edit(
                    query,
                    "🗑️ <b>تأكيد حذف المسابقة</b>\nهل أنت متأكد؟",
                    admin_comp_delete_confirm_keyboard(comp_id)
                )
                return

            if tail.startswith("del_"):
                comp_id = int(tail.split("_")[-1])
                delete_competition(comp_id)
                await _safe_edit(query, "✅ تم حذف المسابقة.", admin_keyboard())
                return

            # End competition
            if tail.startswith("end_"):
                comp_id = int(tail.split("_")[-1])
                leaders = get_competition_leaderboard(comp_id, 1)
                winner_id = leaders[0]['user_id'] if leaders else None
                end_competition(comp_id, winner_id)
                # Notify winner
                if winner_id:
                    comp = get_competition(comp_id)
                    try:
                        await context.bot.send_message(
                            chat_id=winner_id,
                            text=(
                                f"🎉 <b>مبروك! لقد فزت في المسابقة!</b>\n\n"
                                f"🏆 {_html.escape(comp['title'])}\n\n"
                                f"تواصل مع الأدمن لاستلام جائزتك:\n"
                                f"<a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>"
                            ),
                            parse_mode=ParseMode.HTML
                        )
                    except Exception:
                        pass
                await _safe_edit(query, "🏁 <b>تم إنهاء المسابقة</b>", admin_keyboard())
                return

            # Edit competition fields
            if tail.startswith("edit_"):
                comp_id = int(tail.split("_")[-1])
                await _safe_edit(
                    query,
                    "✏️ <b>تعديل المسابقة</b>\nاختر الحقل:",
                    admin_comp_edit_field_keyboard(comp_id)
                )
                return

            # Leaderboard
            if tail.startswith("leaderboard_"):
                comp_id = int(tail.split("_")[-1])
                comp    = get_competition(comp_id)
                leaders = get_competition_leaderboard(comp_id, 15)
                req     = comp.get('required_invites', 15) if comp else 15
                lines   = []
                medals  = ["🥇", "🥈", "🥉"]
                for i, row in enumerate(leaders):
                    medal = medals[i] if i < 3 else f"{i+1}."
                    name  = _html.escape(row.get('first_name') or row.get('username') or str(row['user_id']))
                    lines.append(f"{medal} {name} — {row['invite_count']}/{req}")
                text = (
                    f"🏅 <b>المتصدرون</b>\n"
                    f"🏆 {_html.escape(comp['title'] if comp else '')}\n"
                    f"{_divider()}\n\n"
                    + ("\n".join(lines) if lines else "<i>لا مشاركون</i>")
                )
                await _safe_edit(query, text, admin_competition_detail_keyboard(comp_id, comp.get('status','active') if comp else 'active'))
                return

            # Competition detail (must be last)
            if tail.isdigit():
                comp_id = int(tail)
                comp    = get_competition(comp_id)
                if not comp:
                    await query.answer("❌ المسابقة غير موجودة")
                    return
                participants = get_competition_participants_count(comp_id)
                text = (
                    f"🏆 <b>{_html.escape(comp['title'])}</b>\n"
                    f"{_divider()}\n"
                    f"📝 {_html.escape(comp.get('description',''))}\n\n"
                    f"🎯 الهدف: <b>{comp['required_invites']}</b> دعوة\n"
                    f"👥 المشاركون: <b>{participants}</b>\n"
                    f"📊 الحالة: <b>{'🟢 نشطة' if comp['status']=='active' else '⚫ منتهية'}</b>"
                )
                if comp.get('image_path'):
                    try:
                        if query.message.photo:
                            await query.message.edit_caption(
                                caption=text, parse_mode=ParseMode.HTML,
                                reply_markup=admin_competition_detail_keyboard(comp_id, comp['status'])
                            )
                        else:
                            await query.message.delete()
                            with open(comp["image_path"], "rb") as f:
                                await query.message.reply_photo(
                                    photo=f, caption=text, parse_mode=ParseMode.HTML,
                                    reply_markup=admin_competition_detail_keyboard(comp_id, comp['status'])
                                )
                        return
                    except Exception:
                        pass
                await _safe_edit(query, text, admin_competition_detail_keyboard(comp_id, comp['status']))
                return

        # Edit competition field value
        if data.startswith("admin_compfield_"):
            parts   = data.split("_")
            comp_id = int(parts[2])
            field   = parts[3]
            context.user_data[STATE]     = S_COMP_EDIT_PHOTO if field == "photo" else S_COMP_EDIT_VALUE
            context.user_data[EDIT_ID]   = comp_id
            context.user_data[EDIT_FIELD] = field
            if field == "photo":
                await _safe_edit(query, "📸 أرسل الصورة الجديدة للمسابقة:", back_to_admin_keyboard())
            else:
                labels = {
                    "title": "العنوان", "description": "الوصف",
                    "required_invites": "عدد الدعوات المطلوبة",
                }
                await _safe_edit(
                    query,
                    f"✏️ أدخل القيمة الجديدة لـ «{labels.get(field, field)}»:",
                    back_to_admin_keyboard()
                )
            return

    if data in ("noop", "admin_no_url"):
        await query.answer("افتح من الرابط الخارجي", show_alert=True)
        return


# ══════════════════════════════════════════════
#  MESSAGE HANDLER (admin conversation)
# ══════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user  = update.effective_user
    state = context.user_data.get(STATE, S_IDLE)

    if state == S_IDLE:
        return
    if not _is_admin(user.id):
        return

    text = (update.message.text or "").strip()

    # ── Add account flow ─────────────────────────────────────
    if state == S_ADD_NAME:
        context.user_data[DRAFT]["name"] = text
        context.user_data[STATE] = S_ADD_YEAR
        await update.message.reply_text(
            "📅 <b>سنة الإنشاء</b>\nأدخل سنة الإنشاء (مثال: 2010)\nأو <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_YEAR:
        if text == "-":
            context.user_data[DRAFT]["creation_year"] = None
        elif text.isdigit() and 2006 <= int(text) <= 2025:
            context.user_data[DRAFT]["creation_year"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل سنة بين 2006-2025 أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_PRICE
        await update.message.reply_text("💰 <b>السعر</b>\nأدخل السعر بالدولار (مثال: 25.00)", parse_mode=ParseMode.HTML)

    elif state == S_ADD_PRICE:
        try:
            price = float(text)
            assert price >= 0
        except (ValueError, AssertionError):
            await update.message.reply_text("⚠️ أدخل رقماً صحيحاً للسعر")
            return
        context.user_data[DRAFT]["price"] = price
        context.user_data[STATE] = S_ADD_EMAIL
        await update.message.reply_text("📧 <b>الإيميل</b>\nأدخل إيميل الحساب أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_EMAIL:
        context.user_data[DRAFT]["email"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_PASSWORD
        await update.message.reply_text("🔑 <b>الباسورد</b>\nأدخل باسورد الحساب أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_PASSWORD:
        context.user_data[DRAFT]["password"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_FOLLOWERS
        await update.message.reply_text("👥 <b>عدد المتابعين</b>\nأدخل العدد أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_FOLLOWERS:
        if text == "-":
            context.user_data[DRAFT]["followers"] = 0
        elif text.isdigit():
            context.user_data[DRAFT]["followers"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل رقماً أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_TWEETS
        await update.message.reply_text("🐦 <b>عدد التغريدات</b>\nأدخل العدد أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_TWEETS:
        if text == "-":
            context.user_data[DRAFT]["tweets_count"] = 0
        elif text.isdigit():
            context.user_data[DRAFT]["tweets_count"] = int(text)
        else:
            await update.message.reply_text("⚠️ أدخل رقماً أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_ADD_FEATURES
        await update.message.reply_text("⭐ <b>المميزات</b>\nأدخل مميزات الحساب أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_FEATURES:
        context.user_data[DRAFT]["features"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_DESC
        await update.message.reply_text("📋 <b>الوصف</b>\nأدخل وصفاً للحساب أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_ADD_DESC:
        context.user_data[DRAFT]["description"] = "" if text == "-" else text
        context.user_data[STATE] = S_ADD_PHOTO
        await update.message.reply_text(
            "📸 <b>الصورة</b>\nأرسل صورة للحساب أو أرسل <code>-</code> للتخطي",
            parse_mode=ParseMode.HTML
        )

    elif state == S_ADD_PHOTO:
        if text == "-":
            await _save_account_draft(update, context)

    elif state == S_EDIT_VALUE:
        acc_id = context.user_data.get(EDIT_ID)
        field  = context.user_data.get(EDIT_FIELD)
        if not acc_id or not field:
            return
        val = text
        if field == "price":
            try:
                val = float(text)
            except ValueError:
                await update.message.reply_text("⚠️ أدخل رقماً صحيحاً")
                return
        elif field in ("followers", "tweets_count", "creation_year"):
            if text == "-":
                val = None
            elif text.isdigit():
                val = int(text)
            else:
                await update.message.reply_text("⚠️ أدخل رقماً أو <code>-</code>", parse_mode=ParseMode.HTML)
                return
        update_account(acc_id, **{field: val})
        context.user_data.clear()
        acc = get_account(acc_id)
        await update.message.reply_text(
            f"✅ تم تحديث «{field}»\n\n{_account_card(acc, show_private=True)}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_account_keyboard(acc_id)
        )

    # ── Competition flow ──────────────────────────────────────
    elif state == S_COMP_TITLE:
        context.user_data[DRAFT]["title"] = text
        context.user_data[STATE] = S_COMP_DESC
        await update.message.reply_text("📝 <b>وصف المسابقة</b>\nأدخل وصفاً أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_COMP_DESC:
        context.user_data[DRAFT]["description"] = "" if text == "-" else text
        context.user_data[STATE] = S_COMP_INVITES
        await update.message.reply_text(
            f"🎯 <b>عدد الدعوات المطلوبة للفوز</b>\nاكتب رقماً (الافتراضي: 15):",
            parse_mode=ParseMode.HTML
        )

    elif state == S_COMP_INVITES:
        if text.isdigit() and int(text) > 0:
            context.user_data[DRAFT]["required_invites"] = int(text)
        elif text == "-":
            context.user_data[DRAFT]["required_invites"] = 15
        else:
            await update.message.reply_text("⚠️ أدخل رقماً موجباً أو <code>-</code>", parse_mode=ParseMode.HTML)
            return
        context.user_data[STATE] = S_COMP_PHOTO
        await update.message.reply_text("📸 <b>صورة المسابقة</b>\nأرسل صورة أو <code>-</code>", parse_mode=ParseMode.HTML)

    elif state == S_COMP_PHOTO:
        if text == "-":
            await _save_competition_draft(update, context, image_path=None)

    elif state == S_COMP_EDIT_VALUE:
        comp_id = context.user_data.get(EDIT_ID)
        field   = context.user_data.get(EDIT_FIELD)
        if not comp_id or not field:
            return
        val = text
        if field == "required_invites":
            if text.isdigit() and int(text) > 0:
                val = int(text)
            else:
                await update.message.reply_text("⚠️ أدخل رقماً موجباً")
                return
        update_competition(comp_id, **{field: val})
        context.user_data.clear()
        comp = get_competition(comp_id)
        await update.message.reply_text(
            f"✅ تم التحديث\n🏆 {_html.escape(comp['title'] if comp else '')}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_competition_detail_keyboard(comp_id, comp.get('status','active') if comp else 'active')
        )


async def _save_account_draft(update, context) -> None:
    draft = context.user_data.get(DRAFT, {})
    acc_id = add_account(
        name=draft.get("name", "بدون اسم"),
        description=draft.get("description", ""),
        price=draft.get("price", 0),
        creation_year=draft.get("creation_year"),
        email=draft.get("email", ""),
        password=draft.get("password", ""),
        followers=draft.get("followers", 0),
        tweets_count=draft.get("tweets_count", 0),
        features=draft.get("features", ""),
        image_path=draft.get("image_path"),
    )
    context.user_data.clear()
    acc = get_account(acc_id)
    await update.message.reply_text(
        f"✅ <b>تم إضافة الحساب #{acc_id}</b>\n\n{_account_card(acc, show_private=True)}",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard()
    )


async def _save_competition_draft(update, context, image_path=None) -> None:
    draft  = context.user_data.get(DRAFT, {})
    comp_id = create_competition(
        title=draft.get("title", "مسابقة جديدة"),
        description=draft.get("description", ""),
        image_path=image_path or draft.get("image_path"),
        required_invites=draft.get("required_invites", 15),
    )
    context.user_data.clear()
    comp = get_competition(comp_id)
    await update.message.reply_text(
        f"✅ <b>تم إنشاء المسابقة #{comp_id}</b>\n🏆 {_html.escape(comp['title'])}",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard()
    )


# ══════════════════════════════════════════════
#  PHOTO HANDLER
# ══════════════════════════════════════════════

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user  = update.effective_user
    state = context.user_data.get(STATE, S_IDLE)
    if not _is_admin(user.id):
        return

    photo    = update.message.photo[-1]
    file_obj = await photo.get_file()

    import os as _os
    _os.makedirs("static/images/accounts", exist_ok=True)

    if state in (S_ADD_PHOTO, S_EDIT_PHOTO):
        filename = f"static/images/accounts/acc_{photo.file_unique_id}.jpg"
        await file_obj.download_to_drive(filename)

        if state == S_ADD_PHOTO:
            context.user_data[DRAFT]["image_path"] = filename
            await _save_account_draft(update, context)

        elif state == S_EDIT_PHOTO:
            acc_id = context.user_data.get(EDIT_ID)
            if acc_id:
                update_account(acc_id, image_path=filename)
                context.user_data.clear()
                acc = get_account(acc_id)
                await update.message.reply_text(
                    f"✅ <b>تم تحديث الصورة</b>\n\n{_account_card(acc, show_private=True)}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=admin_account_keyboard(acc_id)
                )

    elif state in (S_COMP_PHOTO, S_COMP_EDIT_PHOTO):
        filename = f"static/images/accounts/comp_{photo.file_unique_id}.jpg"
        await file_obj.download_to_drive(filename)

        if state == S_COMP_PHOTO:
            context.user_data[DRAFT]["image_path"] = filename
            await _save_competition_draft(update, context, image_path=filename)

        elif state == S_COMP_EDIT_PHOTO:
            comp_id = context.user_data.get(EDIT_ID)
            if comp_id:
                update_competition(comp_id, image_path=filename)
                context.user_data.clear()
                await update.message.reply_text(
                    "✅ <b>تم تحديث صورة المسابقة</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=admin_keyboard()
                )


# ══════════════════════════════════════════════
#  PAYMENT HANDLERS
# ══════════════════════════════════════════════

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    try:
        parts  = query.invoice_payload.split("_")
        acc_id = int(parts[1])
        account = get_account(acc_id)
        if account and account['status'] in ('available', 'reserved'):
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="❌ هذا الحساب لم يعد متاحاً.")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await query.answer(ok=False, error_message="❌ حدث خطأ، تواصل مع الأدمن.")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user    = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    try:
        acc_id   = int(payload.split("_")[1])
        order_id = create_order(acc_id, user.id, user.username or "")
        update_account(acc_id, status='sold')
        update_order(order_id, 'completed')
        order = get_order(order_id)
        delivered = await _deliver_account(context.bot, user.id, order)
        if not delivered:
            await update.message.reply_text(
                "✅ <b>تم الدفع بنجاح</b>\nسيتم إرسال بيانات الحساب خلال دقائق.",
                parse_mode=ParseMode.HTML
            )
        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"⭐ <b>دفع نجوم ناجح!</b>\n"
                    f"الحساب: #{acc_id}\n"
                    f"المشتري: @{user.username or user.id}\n"
                    f"الطلب: #{order_id}"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Payment handler error: {e}")
        await update.message.reply_text(
            "⚠️ <b>حدث خطأ بعد الدفع</b>\nتواصل مع الأدمن فوراً.",
            parse_mode=ParseMode.HTML
        )
