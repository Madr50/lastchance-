# bot.py
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, SHOP_NAME
from database import get_all_accounts, get_account, create_order

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== أوامر البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # زر فتح المتجر (Mini App)
    keyboard = [
        [InlineKeyboardButton("🛒 فتح المتجر", web_app=WebAppInfo(url="https://YOUR_DOMAIN.com/mini_app/index.html"))],
        [InlineKeyboardButton("📞 تواصل معنا", url="https://t.me/YOUR_USERNAME")],
        [InlineKeyboardButton("❓ كيفية الشراء", callback_data="how_to_buy")]
    ]
    
    welcome_text = f"""
👋 أهلاً بك *{user.first_name}* في *{SHOP_NAME}*!

🐦 نبيع حسابات Twitter/X إنشاءات قديمة
✅ حسابات موثوقة وآمنة
💳 دفع آمن وسريع

📱 اضغط على الزر أدناه لفتح المتجر
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الحسابات المتاحة مباشرة في البوت (بدون Mini App)"""
    accounts = get_all_accounts()
    
    if not accounts:
        await update.message.reply_text("😔 لا توجد حسابات متاحة حالياً.")
        return
    
    for acc in accounts:
        acc_id, name, desc, price, category, img_path, status, created, updated, meta = acc
        
        # بناء نص المنتج
        text = f"""
📦 *{name}*
💰 السعر: *{price}$*
📋 {desc or 'لا يوجد وصف'}
🏷️ الحالة: {'✅ متاح' if status == 'available' else '❌ مباع'}
        """
        
        # أزرار المنتج
        keyboard = [
            [InlineKeyboardButton("🛒 شراء الآن", callback_data=f"buy_{acc_id}")],
            [InlineKeyboardButton("📱 فتح في المتجر", web_app=WebAppInfo(url=f"https://YOUR_DOMAIN.com/mini_app/index.html?account={acc_id}"))]
        ]
        
        # إرسال الصورة مع النص إن وجدت
        if img_path and os.path.exists(img_path):
            with open(img_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فتح لوحة التحكم للأدمن فقط"""
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول!")
        return
    
    keyboard = [
        [InlineKeyboardButton("⚙️ لوحة التحكم", web_app=WebAppInfo(url="https://YOUR_DOMAIN.com/mini_app/admin.html"))],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats")]
    ]
    
    await update.message.reply_text(
        "🔐 *لوحة التحكم*\n\nاختر ما تريد:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("buy_"):
        acc_id = int(data.split("_")[1])
        account = get_account(acc_id)
        
        if not account or account[6] != 'available':  # status index
            await query.edit_message_text("❌ هذا الحساب غير متاح!")
            return
        
        # إنشاء طلب
        order_id = create_order(acc_id, query.from_user.id, query.from_user.username or "unknown")
        
        await query.edit_message_text(
            f"""
✅ تم حجز الحساب!

🆔 رقم الطلب: `{order_id}`
📦 {account[1]}
💰 السعر: {account[3]}$

💬 تواصل مع الأدمن لإتمام الدفع:
@YOUR_USERNAME
            """,
            parse_mode='Markdown'
        )
    
    elif data == "how_to_buy":
        await query.edit_message_text("""
📖 *كيفية الشراء:*

1️⃣ اضغط على "فتح المتجر"
2️⃣ اختر الحساب اللي بدك ياه
3️⃣ اضغط "شراء"
4️⃣ رح يجيك رقم الطلب
5️⃣ تواصل مع الأدمن وابعثله رقم الطلب
6️⃣ بعد الدفع، ببعتلك بيانات الحساب

✨ سهل وسريع!
        """, parse_mode='Markdown')

# ==================== تشغيل البوت ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
