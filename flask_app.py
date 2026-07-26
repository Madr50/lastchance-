# flask_app.py — Complete Flask web app with all API endpoints
import os
import logging
import threading
import asyncio
from flask import Flask, request, jsonify, render_template, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

from auth_middleware import admin_required, is_session_admin, get_user_from_request
from database import (
    get_all_accounts, get_all_accounts_admin, get_account,
    add_account, update_account, delete_account,
    get_all_orders, get_pending_orders, update_order, get_stats,
    create_order, get_order,
    get_all_competitions, get_active_competitions, get_competition,
    create_competition, update_competition, end_competition, delete_competition,
    get_competition_leaderboard, get_competition_participants_count,
    get_all_users,
)
from config import ADMIN_ID, ADMIN_PASSWORD, ADMIN_USERNAME, SHOP_NAME, USDT_ADDRESS

logger = logging.getLogger(__name__)

UPLOAD_FOLDER      = "static/images/accounts"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-me-in-prod-123!")
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
CORS(app, supports_credentials=True)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(f: str) -> bool:
    return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _fmt_account_public(a: dict) -> dict:
    image = None
    if a.get("image_path") and os.path.exists(a["image_path"]):
        image = "/" + a["image_path"].replace("\\", "/")
    return {
        "id":            a["id"],
        "name":          a["name"],
        "description":   a.get("description") or "",
        "price":         a["price"],
        "creation_year": a.get("creation_year"),
        "category":      a.get("category", "twitter"),
        "status":        a["status"],
        "followers":     a.get("followers") or 0,
        "tweets_count":  a.get("tweets_count") or 0,
        "features":      a.get("features") or "",
        "image":         image,
    }


def _image_url(path: str):
    if path and os.path.exists(path):
        return "/" + path.replace("\\", "/")
    return None


def _get_buyer_from_request():
    """Extract buyer id and username from Telegram initData or return defaults."""
    buyer_id       = 0
    buyer_username = "webapp_user"
    init_data = (
        request.headers.get("X-Init-Data")
        or request.form.get("initData")
        or (request.get_json(silent=True) or {}).get("initData")
    )
    if init_data:
        from auth_middleware import verify_telegram_init_data
        user = verify_telegram_init_data(init_data)
        if user:
            buyer_id       = int(user.get("id", 0))
            buyer_username = user.get("username") or user.get("first_name") or "unknown"
    return buyer_id, buyer_username


def _notify_admin_async(msg: str, order_id: int):
    """Send async admin notification in a background thread."""
    from config import BOT_TOKEN
    if not BOT_TOKEN:
        return
    try:
        from telegram import Bot
        from bot_keyboards import admin_order_keyboard
        kb = admin_order_keyboard(order_id)
        asyncio.run(Bot(BOT_TOKEN).send_message(
            chat_id=ADMIN_ID, text=msg, parse_mode="HTML", reply_markup=kb
        ))
    except Exception as exc:
        logger.warning(f"Admin notify failed: {exc}")


# ══════════════════════════════════════════════
#  STATIC / PAGES
# ══════════════════════════════════════════════

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/health")
@app.route("/ping")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/")
def index():
    return render_template("index.html", admin_username=ADMIN_USERNAME, shop_name=SHOP_NAME)


@app.route("/admin")
def admin():
    return render_template("admin.html", shop_name=SHOP_NAME)


# ══════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data     = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        session.permanent   = True
        return jsonify({"success": True})
    return jsonify({"error": "كلمة المرور غير صحيحة"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/admin/check", methods=["GET"])
def api_admin_check():
    if is_session_admin():
        return jsonify({"authed": True, "via": "session"})
    user = get_user_from_request()
    if user and int(user.get("id", 0)) == ADMIN_ID:
        return jsonify({"authed": True, "via": "telegram"})
    return jsonify({"authed": False}), 403


# ══════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════

@app.route("/api/accounts", methods=["GET"])
def api_get_accounts():
    accounts = get_all_accounts(status="available")
    return jsonify([_fmt_account_public(a) for a in accounts])


@app.route("/api/accounts/<int:account_id>", methods=["GET"])
def api_get_account(account_id):
    acc = get_account(account_id)
    if not acc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_fmt_account_public(acc))


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())


@app.route("/api/competitions", methods=["GET"])
def api_competitions():
    comps = get_active_competitions()
    return jsonify(comps)


# ── USDT Buy (creates a pending order) ─────────────────────
@app.route("/api/buy", methods=["POST"])
def api_buy():
    body       = request.get_json(silent=True) or {}
    acc_id_raw = body.get("account_id") or request.form.get("account_id")
    if not acc_id_raw:
        return jsonify({"error": "account_id is required"}), 400
    try:
        acc_id = int(acc_id_raw)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid account_id"}), 400

    account = get_account(acc_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    if account["status"] != "available":
        return jsonify({"error": "الحساب غير متاح حالياً"}), 409

    buyer_id, buyer_username = _get_buyer_from_request()
    order_id = create_order(acc_id, buyer_id, buyer_username)
    update_account(acc_id, status="reserved")

    msg = (
        f"🛒 <b>طلب USDT جديد #{order_id}</b>\n"
        f"الحساب: {account['name']}\n"
        f"المشتري: @{buyer_username}\n"
        f"السعر: ${account['price']:.2f}"
    )
    threading.Thread(
        target=_notify_admin_async, args=(msg, order_id), daemon=True
    ).start()

    return jsonify({
        "success":      True,
        "order_id":     order_id,
        "account_name": account["name"],
        "price":        account["price"],
        "usdt_address": USDT_ADDRESS,
    }), 201


# ── Stars Invoice (creates a Telegram Stars invoice link) ──
@app.route("/api/create_invoice", methods=["POST"])
def api_create_invoice():
    """Create a Telegram Stars invoice link for mini-app payment."""
    body       = request.get_json(silent=True) or {}
    acc_id_raw = body.get("account_id") or request.form.get("account_id")
    if not acc_id_raw:
        return jsonify({"error": "account_id is required"}), 400
    try:
        acc_id = int(acc_id_raw)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid account_id"}), 400

    account = get_account(acc_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    if account["status"] != "available":
        return jsonify({"error": "الحساب غير متاح حالياً"}), 409

    from config import BOT_TOKEN
    if not BOT_TOKEN:
        return jsonify({"error": "البوت غير مهيأ"}), 503

    from bot_keyboards import usd_to_stars
    stars = usd_to_stars(float(account["price"]))

    try:
        from telegram import Bot, LabeledPrice

        async def _create_link():
            bot = Bot(BOT_TOKEN)
            link = await bot.create_invoice_link(
                title=f"🐦 {account['name']}",
                description=f"حساب تويتر قديم • ${account['price']:.2f}",
                payload=f"account_{acc_id}",
                currency="XTR",
                prices=[LabeledPrice(label=account["name"], amount=stars)],
            )
            return link

        invoice_link = asyncio.run(_create_link())
        return jsonify({"success": True, "invoice_link": invoice_link})

    except Exception as e:
        logger.error(f"create_invoice_link error: {e}")
        return jsonify({"error": "فشل إنشاء الفاتورة، تواصل مع الأدمن"}), 500


# ══════════════════════════════════════════════
#  ADMIN API — ACCOUNTS
# ══════════════════════════════════════════════

@app.route("/api/admin/accounts", methods=["GET"])
@admin_required
def api_admin_accounts():
    status = request.args.get("status", "").strip()
    accs = get_all_accounts_admin()
    if status:
        accs = [a for a in accs if a.get("status") == status]
    for a in accs:
        a["image"] = _image_url(a.get("image_path"))
    return jsonify(accs)


@app.route("/api/admin/accounts", methods=["POST"])
@admin_required
def api_admin_add_account():
    data     = request.form or request.get_json(silent=True) or {}
    name     = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    image_path = None
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

    acc_id = add_account(
        name=name,
        description=data.get("description", ""),
        price=float(data.get("price", 0) or 0),
        creation_year=int(data.get("creation_year") or 0) or None,
        email=data.get("email", ""),
        password=data.get("password", ""),
        followers=int(data.get("followers") or 0),
        tweets_count=int(data.get("tweets_count") or 0),
        features=data.get("features", ""),
        image_path=image_path,
    )
    return jsonify({"success": True, "id": acc_id}), 201


@app.route("/api/admin/accounts/<int:account_id>", methods=["PUT"])
@admin_required
def api_admin_update_account(account_id):
    data   = request.form or request.get_json(silent=True) or {}
    kwargs = {}
    for field in ("name", "description", "email", "password", "features", "status"):
        if field in data:
            kwargs[field] = data[field]
    for int_field in ("creation_year", "followers", "tweets_count"):
        if int_field in data:
            try:
                kwargs[int_field] = int(data[int_field]) if data[int_field] else None
            except ValueError:
                pass
    if "price" in data:
        try:
            kwargs["price"] = float(data["price"])
        except ValueError:
            pass
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename            = secure_filename(file.filename)
            kwargs["image_path"] = os.path.join(UPLOAD_FOLDER, filename)
            file.save(kwargs["image_path"])
    if kwargs:
        update_account(account_id, **kwargs)
    return jsonify({"success": True})


@app.route("/api/admin/accounts/<int:account_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_account(account_id):
    delete_account(account_id)
    return jsonify({"success": True})


# ══════════════════════════════════════════════
#  ADMIN API — ORDERS
# ══════════════════════════════════════════════

@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def api_admin_orders():
    return jsonify(get_all_orders())


@app.route("/api/admin/orders/<int:order_id>", methods=["PUT"])
@admin_required
def api_admin_update_order(order_id):
    data   = request.get_json(silent=True) or {}
    status = data.get("status", "completed")
    update_order(order_id, status)
    return jsonify({"success": True})


# ══════════════════════════════════════════════
#  ADMIN API — STATS / USERS
# ══════════════════════════════════════════════

@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    return jsonify(get_stats())


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    return jsonify(get_all_users())


# ══════════════════════════════════════════════
#  ADMIN API — COMPETITIONS
# ══════════════════════════════════════════════

@app.route("/api/admin/competitions", methods=["GET"])
@admin_required
def api_admin_get_competitions():
    comps = get_all_competitions()
    result = []
    for c in comps:
        c["participants"] = get_competition_participants_count(c["id"])
        c["image"] = _image_url(c.get("image_path"))
        result.append(c)
    return jsonify(result)


@app.route("/api/admin/competitions", methods=["POST"])
@admin_required
def api_admin_add_competition():
    data = request.form or request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400

    image_path = None
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

    comp_id = create_competition(
        title=title,
        description=data.get("description", ""),
        image_path=image_path,
        required_invites=int(data.get("required_invites", 15) or 15),
    )
    return jsonify({"success": True, "id": comp_id}), 201


@app.route("/api/admin/competitions/<int:comp_id>", methods=["PUT"])
@admin_required
def api_admin_update_competition(comp_id):
    data   = request.form or request.get_json(silent=True) or {}
    kwargs = {}
    for field in ("title", "description", "status"):
        if field in data:
            kwargs[field] = data[field]
    if "required_invites" in data:
        try:
            kwargs["required_invites"] = int(data["required_invites"])
        except ValueError:
            pass
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename            = secure_filename(file.filename)
            path                = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            kwargs["image_path"] = path
    if kwargs:
        update_competition(comp_id, **kwargs)
    return jsonify({"success": True})


@app.route("/api/admin/competitions/<int:comp_id>/end", methods=["POST"])
@admin_required
def api_admin_end_competition(comp_id):
    leaders   = get_competition_leaderboard(comp_id, 1)
    winner_id = leaders[0]["user_id"] if leaders else None
    end_competition(comp_id, winner_id)
    return jsonify({"success": True, "winner_id": winner_id})


@app.route("/api/admin/competitions/<int:comp_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_competition(comp_id):
    delete_competition(comp_id)
    return jsonify({"success": True})


@app.route("/api/admin/competitions/<int:comp_id>/leaderboard", methods=["GET"])
@admin_required
def api_admin_comp_leaderboard(comp_id):
    return jsonify(get_competition_leaderboard(comp_id, 50))


# ══════════════════════════════════════════════
#  CUSTOMER ORDERS (Mini App)
# ══════════════════════════════════════════════

@app.route("/api/orders", methods=["POST"])
def api_create_order():
    """Alias for /api/buy — create a USDT order from the Mini App."""
    return api_buy()


@app.route("/api/orders/<int:order_id>/confirm", methods=["POST"])
def api_confirm_order(order_id):
    """Mark USDT as sent and notify admin."""
    order = get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    update_order(order_id, "pending_confirmation")

    account = get_account(order["account_id"])
    buyer_username = order.get("buyer_username") or "unknown"
    acc_name  = account["name"]  if account else "—"
    acc_price = f"${account['price']:.2f}" if account else "—"

    msg = (
        f"💎 <b>إشعار دفع USDT #{order_id}</b>\n"
        f"الحساب: {acc_name}\n"
        f"المشتري: @{buyer_username}\n"
        f"السعر: {acc_price}\n\n"
        f"⏳ في انتظار تأكيد الأدمن."
    )
    threading.Thread(
        target=_notify_admin_async, args=(msg, order_id), daemon=True
    ).start()

    return jsonify({"success": True, "order_id": order_id})
