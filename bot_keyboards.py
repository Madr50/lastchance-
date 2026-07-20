# bot_keyboards.py
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", "")


def shop_url(path=""):
    base = f"https://{DOMAIN}" if DOMAIN else "https://YOUR_DOMAIN.repl.co"
    return base + path


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Open Shop", web_app=WebAppInfo(url=shop_url("/")))],
        [
            InlineKeyboardButton("📞 Contact Admin", url="https://t.me/l825h"),
            InlineKeyboardButton("❓ How to Buy", callback_data="how_to_buy"),
        ],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Admin Panel", web_app=WebAppInfo(url=shop_url("/admin")))],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
    ])


def account_card_keyboard(acc_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{acc_id}")],
        [InlineKeyboardButton("🔍 View in Shop", web_app=WebAppInfo(url=shop_url(f"/?account={acc_id}")))],
    ])
