# wsgi.py — Production entry point for Gunicorn (Render / Amazon Linux)
# Starts the Telegram bot in a background thread, then exposes the Flask app.
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def _start_bot() -> None:
    try:
        from config import BOT_TOKEN
        if not BOT_TOKEN:
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
        bot_app.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logging.getLogger(__name__).error(f"Bot failed to start: {e}", exc_info=True)


# Start bot once per process (gunicorn preload_app=False → once per worker)
_bot_thread = threading.Thread(target=_start_bot, daemon=True, name="telegram-bot")
_bot_thread.start()

from flask_app import app  # noqa: E402  (must be after bot thread)
