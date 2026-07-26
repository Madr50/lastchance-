# متجر ريبر X — بوت تيليجرام لبيع حسابات X النادرة

بوت تيليجرام احترافي لبيع حسابات تويتر/X القديمة والنادرة، مع Mini App للتصفح، لوحة تحكم ويب، نظام دعوات، ومسابقات.

## تشغيل المشروع

- `python main.py` — تشغيل Flask + بوت التيليجرام معاً (التطوير)
- `gunicorn wsgi:app` — بيئة الإنتاج (Render / VPS)

## Secrets المطلوبة (Replit Secrets 🔒)

| المتغير | الوصف | إجباري |
|---|---|---|
| `BOT_TOKEN` | توكن البوت من @BotFather | ✅ |
| `ADMIN_PASSWORD` | كلمة مرور لوحة التحكم المتصفح | ✅ |
| `SESSION_SECRET` | مفتاح جلسة Flask (عشوائي طويل) | ✅ |
| `ADMIN_ID` | Telegram ID الأدمن | مستحسن |
| `ADMIN_USERNAME` | يوزر الأدمن بدون @ | مستحسن |
| `BOT_USERNAME` | يوزر البوت بدون @ | مستحسن |
| `USDT_ADDRESS` | عنوان محفظة USDT TRC20 | للدفع |
| `SHOP_NAME` | اسم المتجر | اختياري |

## المكدس التقني

- **Backend**: Python 3, Flask 3, python-telegram-bot 21
- **Database**: SQLite (WAL mode, thread-safe)
- **Web**: Jinja2 templates + Vanilla JS + CSS
- **Deploy**: Gunicorn (wsgi.py)

## بنية الملفات

```
main.py          — نقطة البداية (Flask + Bot thread)
wsgi.py          — Gunicorn entry point
flask_app.py     — كل API endpoints + تسليم الصفحات
bot_handlers.py  — منطق البوت (commands + callbacks)
bot_keyboards.py — كل InlineKeyboardMarkup layouts
database.py      — SQLite helpers (thread-safe)
config.py        — إعدادات من env vars (لا defaults غير آمنة)
auth_middleware.py — Telegram initData validation + session auth
templates/
  index.html     — Mini App (Telegram WebApp) لتصفح الحسابات
  admin.html     — لوحة التحكم (متصفح عادي)
static/
  css/           — shop.css, admin.css
  js/            — shop.js, admin.js
  images/accounts/ — صور الحسابات (مُستثناة من git)
```

## User preferences

- اللغة العربية في الواجهة والمراسلات
- اسم البوت: متجر ريبر X
- البوت username: (يُعيَّن من ADMIN_USERNAME)
- الثيم: Dark premium (أسود/ذهبي/أزرق)

## ملاحظات مهمة

- **shop.db** مُستثنى من git — لا ترفعه
- كل الـ secrets من Replit Secrets فقط — لا hardcoding
- البوت يعمل على polling (مناسب للتطوير)؛ للإنتاج يُفضَّل webhook
- سلوك تعديل الرسالة (edit_message) مُطبَّق في كل التنقلات
