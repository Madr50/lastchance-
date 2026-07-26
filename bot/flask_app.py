# flask_app.py
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
from config import ADMIN_ID, ADMIN_PASSWORD, ADMIN_USERNAME, SHOP_NAME

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


# ── Static ──────────────────────────────────────────────────
@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ── Health ──────────────────────────────────────────────────
@app.route("/health")
@app.route("/ping")
def health():
    return jsonify({"status": "ok"}), 200


# ── Pages ───────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", admin_username=ADMIN_USERNAME, shop_name=SHOP_NAME)


@app.route("/admin")
def admin():
    return render_template("admin.html", shop_name=SHOP_NAME)


# ── Auth ────────────────────────────────────────────────────
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


# ── Public API ──────────────────────────────────────────────
@app.route("/api/accounts", methods=["GET"])
def api_get_accounts():
    accounts = get_all_accounts(status="available")
    return jsonify([_fmt_account_public(a) for a in accounts])


@app.route("/api/accounts/<int:account_id>", methods=["GET"])
def api_get_account(account_id):
    a = get_account(account_id)
    if not a:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_fmt_account_public(a))


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())


@app.route("/api/competitions", methods=["GET"])
def api_competitions():
    comps = get_active_competitions()
    return jsonify([{
        "id":               c["id"],
        "title":            c["title"],
        "description":      c.get("description") or "",
        "required_invites": c.get("required_invites", 15),
        "status":           c["status"],
        "participants":     get_competition_participants_count(c["id"]),
        "image":            "/" + c["image_path"].replace("\\", "/") if c.get("image_path") and os.path.exists(c["image_path"]) else None,
    } for c in comps])


# ── Public buy ──────────────────────────────────────────────
@app.route("/api/buy", methods=["POST"])
def api_buy():
    body   = request.get_json(silent=True) or {}
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
        return jsonify({"error": "Account not available"}), 409

    # Get buyer from Telegram initData
    buyer_id       = 0
    buyer_username = "webapp_user"
    init_data = (
        request.headers.get("X-Init-Data")
        or body.get("initData")
        or request.form.get("initData")
    )
    if init_data:
        from auth_middleware import verify_telegram_init_data
        user = verify_telegram_init_data(init_data)
        if user:
            buyer_id       = int(user.get("id", 0))
            buyer_username = user.get("username") or user.get("first_name") or "unknown"

    order_id = create_order(acc_id, buyer_id, buyer_username)
    update_account(acc_id, status='reserved')

    # Notify admin
    def _notify_admin():
        from config import BOT_TOKEN
        if not BOT_TOKEN:
            return
        try:
            from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
            from bot_keyboards import admin_order_keyboard
            kb  = admin_order_keyboard(order_id)
            msg = (
                f"🛒 <b>طلب جديد #{order_id}</b>\n"
                f"الحساب: {account['name']}\n"
                f"المشتري: @{buyer_username}\n"
                f"السعر: ${account['price']:.2f}"
            )
            asyncio.run(Bot(BOT_TOKEN).send_message(
                chat_id=ADMIN_ID, text=msg, parse_mode="HTML", reply_markup=kb
            ))
        except Exception as exc:
            logger.warning(f"Admin notify failed: {exc}")

    threading.Thread(target=_notify_admin, daemon=True).start()
    return jsonify({"success": True, "order_id": order_id}), 201


# ══════════════════════════════════════════════
#  ADMIN API
# ══════════════════════════════════════════════

@app.route("/api/admin/accounts", methods=["GET"])
@admin_required
def api_admin_accounts():
    accounts = get_all_accounts_admin()
    result   = []
    for a in accounts:
        d = _fmt_account_public(a)
        d["email"]    = a.get("email") or ""
        d["password"] = a.get("password") or ""
        result.append(d)
    return jsonify(result)


@app.route("/api/admin/accounts", methods=["POST"])
@admin_required
def api_admin_add_account():
    data = request.form
    image_path = None
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

    acc_id = add_account(
        name=data.get("name", ""),
        description=data.get("description", ""),
        price=float(data.get("price", 0) or 0),
        creation_year=int(data.get("creation_year")) if data.get("creation_year") else None,
        category=data.get("category", "twitter"),
        image_path=image_path,
        email=data.get("email", ""),
        password=data.get("password", ""),
        followers=int(data.get("followers", 0) or 0),
        tweets_count=int(data.get("tweets_count", 0) or 0),
        features=data.get("features", ""),
    )
    return jsonify({"success": True, "id": acc_id}), 201


@app.route("/api/admin/accounts/<int:account_id>", methods=["PUT"])
@admin_required
def api_admin_update_account(account_id):
    data   = request.form or request.get_json(silent=True) or {}
    kwargs = {}
    for field in ("name", "description", "category", "email", "password", "features", "status"):
        if field in data:
            kwargs[field] = data[field]
    for field in ("price",):
        if field in data:
            try:
                kwargs[field] = float(data[field])
            except ValueError:
                pass
    for field in ("followers", "tweets_count"):
        if field in data:
            try:
                kwargs[field] = int(data[field])
            except ValueError:
                pass
    if "creation_year" in data:
        try:
            kwargs["creation_year"] = int(data["creation_year"]) if data["creation_year"] else None
        except ValueError:
            pass

    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path     = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            kwargs["image_path"] = path

    if kwargs:
        update_account(account_id, **kwargs)
    return jsonify({"success": True})


@app.route("/api/admin/accounts/<int:account_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_account(account_id):
    delete_account(account_id)
    return jsonify({"success": True})


@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def api_admin_orders():
    return jsonify(get_all_orders())


@app.route("/api/admin/orders/<int:order_id>", methods=["PUT"])
@admin_required
def api_admin_update_order(order_id):
    data   = request.get_json(silent=True) or {}
    status = data.get("status")
    if status:
        update_order(order_id, status)
    return jsonify({"success": True})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    return jsonify(get_stats())


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    users = get_all_users()
    return jsonify(users)


# ── Admin Competitions ──────────────────────────────────────
@app.route("/api/admin/competitions", methods=["GET"])
@admin_required
def api_admin_get_competitions():
    comps = get_all_competitions()
    result = []
    for c in comps:
        result.append({
            **c,
            "participants": get_competition_participants_count(c["id"]),
            "image": "/" + c["image_path"].replace("\\", "/") if c.get("image_path") and os.path.exists(c["image_path"]) else None,
        })
    return jsonify(result)


@app.route("/api/admin/competitions", methods=["POST"])
@admin_required
def api_admin_add_competition():
    data       = request.form
    image_path = None
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

    comp_id = create_competition(
        title=data.get("title", "مسابقة"),
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
            filename = secure_filename(file.filename)
            path     = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            kwargs["image_path"] = path
    if kwargs:
        update_competition(comp_id, **kwargs)
    return jsonify({"success": True})


@app.route("/api/admin/competitions/<int:comp_id>/end", methods=["POST"])
@admin_required
def api_admin_end_competition(comp_id):
    leaders   = get_competition_leaderboard(comp_id, 1)
    winner_id = leaders[0]['user_id'] if leaders else None
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
