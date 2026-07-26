````markdown name=README.md
# 🏪 LastChance Marketplace - Telegram Mini App

A powerful Telegram Marketplace Bot with mini app support, featuring listings, orders, payments, and admin dashboard.

**Features:**
- 🤖 Full-featured Telegram Bot
- 🌐 Flask Web App with Mini App support
- 💳 Multiple payment methods (Telegram Stars, USDT, Bank Transfer)
- 📦 Complete marketplace with listings and orders
- 💬 Direct messaging between sellers and buyers
- ⭐ Reviews and ratings system
- 📊 Admin dashboard
- 👥 User profiles and verification

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- SQLite3 (usually pre-installed)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Madr50/lastchance-.git
   cd lastchance-
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

The bot will start polling and Flask server will run on `http://localhost:5000`

---

## 🌍 Deployment

### Deploy to Render.com

1. **Push to GitHub** (with `.env` in `.gitignore`)

2. **Create new Web Service on Render**
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `gunicorn wsgi:app`
   - Set environment variables from `.env.example`

3. **Copy RENDER_EXTERNAL_URL** from Render dashboard to `.env`

### Deploy to Heroku

```bash
heroku create your-app-name
heroku buildpacks:add heroku/python
heroku config:set BOT_TOKEN=your_token
heroku config:set ADMIN_ID=your_admin_id
# ... set all other config vars
git push heroku main
```

### Deploy to Replit

1. Create new Replit project
2. Clone repository
3. Create `.env` file with your credentials
4. Run `python main.py`

---

## 📋 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Telegram
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
ADMIN_USERNAME=your_username

# Web App URLs
RENDER_EXTERNAL_URL=https://your-domain.com
# or for Replit:
REPLIT_DEV_DOMAIN=your-replit-domain.repl.co

# Payments
USDT_TRON_ADDRESS=your_trc20_address
BANK_IBAN=your_iban
BANK_ACCOUNT_NUMBER=your_account

# Commission
COMMISSION_TYPE=percentage
COMMISSION_PERCENT=10

# Admin
ADMIN_PASSWORD=your_admin_password
```

---

## 🏗️ Architecture

```
lastchance-/
├── main.py                 # Entry point (bot + flask)
├── database.py            # SQLite database + ORM
├── config.py              # Configuration & settings
├── bot_handlers.py        # Telegram bot handlers
├── bot_keyboards.py       # Bot inline keyboards
├── flask_app.py           # Flask REST API
├── auth_middleware.py     # Authentication
├── wsgi.py                # WSGI entry for gunicorn
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html         # Marketplace frontend
│   ├── admin.html         # Admin dashboard
│   └── seller.html        # Seller dashboard
├── static/                # Static files (CSS, JS, images)
└── .env.example           # Environment template
```

---

## 🛠️ Database Schema

### Tables

**users** - Marketplace users (buyers & sellers)
- Profile info, verification, ratings, statistics

**listings** - Products for sale
- Title, description, price, images, status

**orders** - Purchase orders
- Buyer, seller, amount, payment method, status

**chats** - Direct messages between users
- Participants, messages, read status

**reviews** - Buyer/seller ratings
- Rating (1-5), comment, verified purchase

**categories** - Product categories
- Name, icon, banner, colors

**payments** - Payment records
- Amount, method, status, transaction ID

**admins** - Admin users
- Permissions, roles, login history

---

## 📱 Bot Commands

### User Commands
- `/start` - Start the bot
- `/help` - Show help
- `/shop` - Browse marketplace
- `/admin` - Admin panel (admin only)

### Inline Buttons
- 🏪 Browse Marketplace
- 📋 Product List
- 💰 Pricing Info
- 📖 How to Buy
- 💬 Contact Us

---

## 💳 Payment Methods

### 1. Telegram Stars
- Built-in Telegram payment
- Instant transactions
- No setup required

### 2. USDT (TRON/TRC20)
- Cryptocurrency payment
- Manual verification
- Set `USDT_TRON_ADDRESS` in config

### 3. Bank Transfer
- Traditional wire transfer
- Manual confirmation by admin
- Set bank details in config

---

## 🔐 Admin Panel

Access admin dashboard at:
- **Web:** `https://your-domain.com/admin`
- **Password:** Set in `ADMIN_PASSWORD`
- **Via Telegram:** Admin commands in bot

### Admin Features
- ➕ Add/edit/delete listings
- 📦 Manage orders
- 👥 Manage users
- 💰 View statistics & revenue
- 📋 Handle reports/disputes
- ⚙️ Configure marketplace settings

---

## 🔧 Configuration

### Commission System

**Percentage-based (default):**
```
COMMISSION_TYPE=percentage
COMMISSION_PERCENT=10  # 10% of each sale
```

**Fixed amount:**
```
COMMISSION_TYPE=fixed
COMMISSION_FIXED=5  # $5 per sale
```

**With limits:**
```
COMMISSION_MIN=1      # Minimum commission
COMMISSION_MAX=100    # Maximum commission
```

### Features

```env
MAINTENANCE_MODE=false           # Disable marketplace
REQUIRE_VERIFICATION=false       # Force user verification
REQUIRE_EMAIL_VERIFICATION=false # Email verification
```

---

## 🧪 Testing

### Test the Bot Locally
```bash
python -c "
from main import _bot_main
import asyncio
asyncio.run(_bot_main())
"
```

### Test the API
```bash
# Get listings
curl http://localhost:5000/api/listings

# Get stats
curl http://localhost:5000/api/stats

# Login to admin
curl -X POST http://localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{\"password\":\"your_admin_password\"}'
```

---

## 🚨 Troubleshooting

### Bot not responding
- Check `BOT_TOKEN` in `.env`
- Verify bot token with [@BotFather](https://t.me/BotFather)
- Check logs for errors

### Database locked
- Stop the application
- Delete `shop.db-shm` and `shop.db-wal` files
- Restart

### Payment not working
- Verify payment credentials in `.env`
- Check USDT address for typos
- Ensure admin is configured

### Web app not loading
- Set `RENDER_EXTERNAL_URL` or `REPLIT_DEV_DOMAIN`
- Verify Flask is running
- Check browser console for errors

---

## 📊 API Endpoints

### Public
- `GET /api/listings` - List all products
- `GET /api/listings/<id>` - Get product details
- `GET /api/stats` - Marketplace statistics
- `GET /api/info` - Marketplace info

### Authentication
- `POST /api/auth/login` - Admin login
- `POST /api/auth/telegram` - Telegram auth
- `GET /api/auth/check` - Check auth status

### Orders
- `POST /api/orders` - Create order
- `GET /api/orders/<id>` - Get order details
- `POST /api/orders/<id>/confirm` - Confirm order

### User
- `GET /api/me` - Current user
- `PUT /api/me` - Update profile
- `GET /api/users/<id>` - User profile

### Admin (requires auth)
- `GET /api/admin/listings` - All listings
- `POST /api/admin/listings` - Add listing
- `PUT /api/admin/listings/<id>` - Edit listing
- `DELETE /api/admin/listings/<id>` - Delete listing
- `GET /api/admin/orders` - All orders
- `PUT /api/admin/orders/<id>` - Update order

---

## 🔐 Security Tips

1. **Never commit `.env`** - Use `.env.example` as template
2. **Change `ADMIN_PASSWORD`** - Use strong password
3. **Use HTTPS** in production - Render/Heroku provide SSL
4. **Keep dependencies updated** - Run `pip install --upgrade -r requirements.txt`
5. **Rotate secrets regularly** - Update `SECRET_KEY` and `SESSION_SECRET`
6. **Limit file uploads** - Set `MAX_CONTENT_LENGTH` appropriately
7. **Use environment variables** - Never hardcode secrets

---

## 📝 License

MIT License - See LICENSE file

---

## 💡 Features Roadmap

- [ ] Email notifications
- [ ] SMS verification
- [ ] Escrow payments
- [ ] Seller analytics
- [ ] Advanced search filters
- [ ] Wishlist/Collections
- [ ] Affiliate program
- [ ] Mobile app

---

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

## 📞 Support

- **Admin:** [@l825h](https://t.me/l825h)
- **Issues:** GitHub Issues
- **Docs:** Check `replit.md` for Replit setup

---

**Made with ❤️ for the Telegram community**
````
