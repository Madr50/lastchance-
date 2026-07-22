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


def run_bot() -> None:
    from config import BOT_TOKEN
    if not BOT_TOKEN:
        logger.warning(
            "BOT_TOKEN is not set — Telegram bot will NOT start. "
            "Set it in environment secrets as BOT_TOKEN."
        )
        return

    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        MessageHandler, filters
    )
    from bot_handlers import (
        cmd_start, cmd_help, cmd_shop, cmd_admin, cmd_cancel,
        button_handler, message_handler, photo_handler
    )

    bot_app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    bot_app.add_handler(CommandHandler("start",  cmd_start))
    bot_app.add_handler(CommandHandler("help",   cmd_help))
    bot_app.add_handler(CommandHandler("shop",   cmd_shop))
    bot_app.add_handler(CommandHandler("admin",  cmd_admin))
    bot_app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Inline button presses
    bot_app.add_handler(CallbackQueryHandler(button_handler))

    # Photo uploads (admin flow)
    bot_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Text messages (admin conversation flow)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("🤖 Telegram bot polling started.")
    bot_app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
    bot_thread.start()

    from flask_app import app as flask_app
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
