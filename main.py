# main.py — Entry point: Flask (main thread) + Telegram bot (background thread)
import logging
import os
import threading

# Load .env file if present (for local/EC2 deployments)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _bot_main() -> None:
    from config import BOT_TOKEN
    if not BOT_TOKEN:
        logger.warning(
            "BOT_TOKEN is not set — Telegram bot will NOT start. "
            "Set it in environment secrets as BOT_TOKEN."
        )
        return

    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        MessageHandler, PreCheckoutQueryHandler, filters
    )
    from bot_handlers import (
        cmd_start, cmd_help, cmd_shop, cmd_admin, cmd_cancel, cmd_test_stars,
        button_handler, message_handler, photo_handler,
        pre_checkout_handler, successful_payment_handler
    )

    bot_app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    bot_app.add_handler(CommandHandler("start",  cmd_start))
    bot_app.add_handler(CommandHandler("help",   cmd_help))
    bot_app.add_handler(CommandHandler("shop",   cmd_shop))
    bot_app.add_handler(CommandHandler("admin",  cmd_admin))
    bot_app.add_handler(CommandHandler("cancel",     cmd_cancel))
    bot_app.add_handler(CommandHandler("test_stars", cmd_test_stars))

    # Inline button presses
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    # ── Telegram Stars payment handlers ────────────────────
    # Must answer pre-checkout within 10 seconds
    bot_app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))

    # Fires after successful Stars payment — delivers account automatically
    bot_app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )

    # Photo uploads (admin flow)
    bot_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Text messages (admin conversation flow)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("🤖 Telegram bot polling started.")
    # Use async context manager to avoid signal-handler errors in non-main threads
    async with bot_app:
        # IMPORTANT: start() must come BEFORE start_polling()
        # start() activates the update processor (dispatches handlers).
        # start_polling() fetches updates from Telegram.
        # Wrong order = updates queue up but never get dispatched → Stars pre_checkout silently dropped.
        await bot_app.start()
        await bot_app.updater.start_polling(
            allowed_updates=["message", "callback_query", "pre_checkout_query"]
        )
        # Keep running until the process exits (daemon thread)
        import asyncio
        await asyncio.Event().wait()


def run_bot() -> None:
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_bot_main())
    finally:
        loop.close()


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
    bot_thread.start()

    from flask_app import app as flask_app
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
