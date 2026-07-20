# bot_handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, SHOP_NAME
from database import get_all_accounts, get_account, create_order, update_account, get_stats
from bot_keyboards import main_menu_keyboard, admin_keyboard, account_card_keyboard

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Welcome *{user.first_name}* to *{SHOP_NAME}*!\n\n"
        "🐦 We sell verified old Twitter/X accounts (2010–2015+)\n"
        "✅ Safe, authentic, and instantly delivered\n"
        "💳 Fast & secure ordering\n\n"
        "👇 Tap below to browse our store"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )


async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = get_all_accounts(status="available")
    if not accounts:
        await update.message.reply_text("😔 No accounts available right now. Check back soon!")
        return

    await update.message.reply_text(
        f"🛒 *Available Accounts* ({len(accounts)} items)\n\nBrowse below 👇",
        parse_mode="Markdown"
    )

    for acc in accounts[:10]:  # Telegram limits
        year_label = f"📅 {acc['creation_year']}" if acc['creation_year'] else ""
        text = (
            f"📦 *{acc['name']}*\n"
            f"💰 Price: *${acc['price']:.2f}*\n"
            f"{year_label}\n"
            f"📋 {acc['description'] or 'No description'}\n"
            f"🏷️ Status: ✅ Available"
        )
        keyboard = account_card_keyboard(acc['id'])

        img = acc.get('image_path')
        try:
            if img:
                import os
                if os.path.exists(img):
                    with open(img, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=text,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                    continue
        except Exception as e:
            logger.warning(f"Could not send photo: {e}")

        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access denied.")
        return

    stats = get_stats()
    text = (
        "🔐 *Admin Dashboard*\n\n"
        f"📦 Total accounts: *{stats['total']}*\n"
        f"✅ Available: *{stats['available']}*\n"
        f"🔴 Sold: *{stats['sold']}*\n"
        f"🟡 Reserved: *{stats['reserved']}*\n"
        f"💰 Revenue: *${stats['revenue']:.2f}*\n"
        f"📋 Total orders: *{stats['total_orders']}*"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=admin_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "how_to_buy":
        await query.edit_message_text(
            "📖 *How to Buy:*\n\n"
            "1️⃣ Open the Shop\n"
            "2️⃣ Browse available accounts\n"
            "3️⃣ Click on an account you like\n"
            "4️⃣ Tap *Buy Now* — you'll get an order ID\n"
            "5️⃣ Contact the admin @l825h with your order ID\n"
            "6️⃣ Pay and receive your account credentials\n\n"
            "✨ Simple, fast, and secure!",
            parse_mode="Markdown"
        )
        return

    if data == "stats":
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text("⛔ Access denied.")
            return
        stats = get_stats()
        await query.edit_message_text(
            f"📊 *Live Statistics*\n\n"
            f"📦 Total accounts: *{stats['total']}*\n"
            f"✅ Available: *{stats['available']}*\n"
            f"🔴 Sold: *{stats['sold']}*\n"
            f"🟡 Reserved: *{stats['reserved']}*\n"
            f"💰 Revenue: *${stats['revenue']:.2f}*\n"
            f"📋 Total orders: *{stats['total_orders']}*",
            parse_mode="Markdown"
        )
        return

    if data.startswith("buy_"):
        acc_id = int(data.split("_")[1])
        account = get_account(acc_id)

        if not account or account['status'] != 'available':
            await query.edit_message_text("❌ This account is no longer available.")
            return

        order_id = create_order(acc_id, query.from_user.id,
                                query.from_user.username or "unknown")
        update_account(acc_id, status='reserved')

        buyer_info = (
            f"🆕 *New Order!*\n\n"
            f"🆔 Order ID: `{order_id}`\n"
            f"📦 Account: {account['name']}\n"
            f"💰 Price: ${account['price']:.2f}\n"
            f"👤 Buyer: @{query.from_user.username or 'unknown'} "
            f"(ID: `{query.from_user.id}`)"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=buyer_info,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")

        await query.edit_message_text(
            f"✅ *Order Placed!*\n\n"
            f"🆔 Order ID: `{order_id}`\n"
            f"📦 {account['name']}\n"
            f"💰 ${account['price']:.2f}\n\n"
            f"💬 Contact admin @l825h with your order ID to complete payment.\n"
            f"⏳ Your account is reserved for 24 hours.",
            parse_mode="Markdown"
        )
