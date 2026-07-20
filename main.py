# main.py — Entry point: Flask (main thread) + Telegram bot (background thread)
import logging
import os
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_bot() -> None:
    """
    Start the Telegram bot (PTB v20).
    run_polling() manages its own event loop — do NOT call asyncio.run() around it.
    """
    from config import BOT_TOKEN
    if not BOT_TOKEN:
        logger.warning(
            "BOT_TOKEN is not set — Telegram bot will NOT start. "
            "Set it in environment secrets as BOT_TOKEN."
        )
        return

    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    from bot_handlers import (
        cmd_start, cmd_help, cmd_shop, cmd_admin, button_handler
    )

    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", cmd_start))
    bot_app.add_handler(CommandHandler("help",  cmd_help))
    bot_app.add_handler(CommandHandler("shop",  cmd_shop))
    bot_app.add_handler(CommandHandler("admin", cmd_admin))
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Telegram bot polling started.")
    bot_app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    # Start bot in background (only active when BOT_TOKEN is set)
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
    bot_thread.start()

    # Flask runs in the main thread
    from flask_app import app as flask_app
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
