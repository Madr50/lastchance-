# 𝕏 Twitter X Shop — Bot + Web Admin

## Overview
A complete Telegram bot + Flask web app for selling old/rare Twitter/X accounts. Features:
- **Telegram Bot**: Full inline account browsing, buy flow, and admin management
- **Mini App (Web)**: Beautiful shop frontend customers see inside Telegram
- **Admin Panel**: `/admin` URL with password-protected dashboard
- **Auto Delivery**: When admin confirms payment → bot auto-sends credentials to buyer

## Stack
- Python 3.12
- Flask 3.x + Flask-CORS
- python-telegram-bot 20.7 (async polling)
- SQLite (WAL mode, thread-safe)
- Vanilla JS + Cairo font (no build step)

## Running
```bash
python main.py
```
Flask starts on port 5000. Bot starts in a background thread (requires `BOT_TOKEN`).

## Environment Secrets Required
| Secret | Description |
|--------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `SESSION_SECRET` | Flask session secret (already set) |
| `ADMIN_PASSWORD` | Web admin panel password (default: `admin1234`) |
| `ADMIN_ID` | Telegram user ID of admin (default: 8989271393) |
| `ADMIN_USERNAME` | Admin Telegram username (default: l825h) |
| `WEBAPP_URL` | HTTPS URL of this app for Telegram WebApp buttons |

## Key Files
- `main.py` — Entry point, starts Flask + bot thread
- `bot_handlers.py` — All Telegram bot logic, admin conversation flows
- `bot_keyboards.py` — Premium keyboard layouts
- `database.py` — SQLite schema + CRUD (auto-migrates new columns)
- `flask_app.py` — REST API + page routes
- `config.py` — Env var config
- `auth_middleware.py` — Session + Telegram initData auth
- `templates/index.html` — Customer shop mini app
- `templates/admin.html` — Admin dashboard

## Bot Commands
- `/start` — Welcome + main menu
- `/shop` — Browse available accounts
- `/admin` — Admin panel (admin only)
- `/cancel` — Cancel current operation

## Admin Bot Flow (adding accounts)
1. `/admin` → press "➕ إضافة حساب"
2. Bot asks step-by-step: name → year → price → email → password → followers → tweets → features → description → photo
3. Account saved with full details
4. Send `/cancel` any time to abort

## Order Flow
1. User browses → presses buy → confirms
2. Admin gets notification with ✅ Confirm / ❌ Reject buttons
3. On confirm → bot automatically sends email+password to buyer

## User Preferences
- RTL Arabic interface throughout
- Dark premium theme (#0d1117 background)
