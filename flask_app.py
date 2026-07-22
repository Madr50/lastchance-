# flask_app.py
import os
import time
import logging
from typing import Optional
from flask import Flask, request, jsonify, render_template, send_from_directory, session

from flask_cors import CORS
from werkzeug.utils import secure_filename

from auth_middleware import admin_required, is_session_admin, get_user_from_request
from database import (
    get_all_accounts, get_all_accounts_admin, get_account,
    add_account, update_account, delete_account,
    get_all_orders, get_pending_orders, update_order, get_stats,
    create_order, get_order
)
from config import ADMIN_ID, ADMIN_PASSWORD

logger = logging.getLogger(__name__)

UPLOAD_FOLDER      = "static/images/accounts"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-me-in-prod-123!")
app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Health ──────────────────────────────────────────────────
@app.route("/health")
@app.route("/ping")
def health():
    return jsonify({"status": "ok"}), 200


# ── Pages ───────────────────────────────────────────────────
@app.route("/")
def index():
    from config import ADMIN_USERNAME, SHOP_NAME
    return render_template("index.html", admin_username=ADMIN_USERNAME, shop_name=SHOP_NAME)


@app.route("/admin")
def admin():
    # The admin panel HTML handles its own auth via JS (password login / Telegram initData).
    # API endpoints behind @admin_required provide the real server-side protection.
    return render_template("admin.html")


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
    return jsonify([_format_account_public(a) for a in accounts])


@app.route("/api/accounts/<int:account_id>", methods=["GET"])
def api_get_account(account_id):
    a = get_account(account_id)
    if not a:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_format_account_public(a))


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())


# ── Public buy ──────────────────────────────────────────────
@app.route("/api/buy", methods=["POST"])
def api_buy():
    import json as _json
    from urllib.parse import unquote

    body       = request.get_json(silent=True) or {}
    acc_id_raw = request.form.get("account_id") or body.get("account_id")
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
        return jsonify({"error": "Account is no longer available"}), 409

    buyer_id, buyer_username = 0, "unknown"
    init_data_raw = request.form.get("initData") or request.headers.get("X-Init-Data", "")
    if init_data_raw:
        try:
            params        = dict(p.split("=", 1) for p in init_data_raw.split("&") if "=" in p)
            user          = _json.loads(unquote(params.get("user", "{}")))
            buyer_id      = user.get("id", 0)
            buyer_username = user.get("username", "unknown")
        except Exception:
            pass

    order_id = create_order(acc_id, buyer_id, buyer_username)
    update_account(acc_id, status="reserved")
    _notify_admin_async(order_id, account, buyer_id, buyer_username)

    return jsonify({
        "success":      True,
        "order_id":     order_id,
        "account_name": account["name"],
        "price":        account["price"],
    })


# ── Admin API ───────────────────────────────────────────────
@app.route("/api/admin/accounts", methods=["GET"])
@admin_required
def api_admin_get_accounts():
    return jsonify([_format_account(a) for a in get_all_accounts_admin()])


@app.route("/api/admin/accounts", methods=["POST"])
@admin_required
def api_admin_create_account():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "الاسم مطلوب"}), 400

    try:
        price = float(request.form.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "السعر غير صحيح"}), 400

    description   = request.form.get("description", "")
    raw_year      = request.form.get("creation_year")
    creation_year = int(raw_year) if raw_year and raw_year.isdigit() else None
    category      = request.form.get("category", "twitter")
    image_path    = _save_upload(request.files.get("image"))
    email         = request.form.get("email", "")
    password      = request.form.get("password", "")
    followers     = int(request.form.get("followers", 0) or 0)
    tweets_count  = int(request.form.get("tweets_count", 0) or 0)
    features      = request.form.get("features", "")

    account_id = add_account(
        name, description, price, creation_year, category, image_path,
        email, password, followers, tweets_count, features
    )
    return jsonify({"success": True, "id": account_id}), 201


@app.route("/api/admin/accounts/<int:account_id>", methods=["PUT"])
@admin_required
def api_admin_update_account(account_id):
    if not get_account(account_id):
        return jsonify({"error": "Not found"}), 404

    updates = {}
    for field in ["name", "description", "status", "category", "email", "password", "features"]:
        if field in request.form:
            updates[field] = request.form[field]
    if "price" in request.form:
        try:
            updates["price"] = float(request.form["price"])
        except (ValueError, TypeError):
            return jsonify({"error": "السعر غير صحيح"}), 400
    for num_field in ["followers", "tweets_count"]:
        if num_field in request.form:
            try:
                updates[num_field] = int(request.form[num_field])
            except (ValueError, TypeError):
                pass
    raw_year = request.form.get("creation_year", "")
    if raw_year and raw_year.isdigit():
        updates["creation_year"] = int(raw_year)

    img = _save_upload(request.files.get("image"))
    if img:
        updates["image_path"] = img

    update_account(account_id, **updates)
    return jsonify({"success": True})


@app.route("/api/admin/accounts/<int:account_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_account(account_id):
    if not get_account(account_id):
        return jsonify({"error": "Not found"}), 404
    delete_account(account_id)
    return jsonify({"success": True})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def api_admin_stats():
    return jsonify(get_stats())


@app.route("/api/admin/orders", methods=["GET"])
@admin_required
def api_admin_orders():
    return jsonify(get_all_orders())


@app.route("/api/admin/orders/<int:order_id>", methods=["PUT"])
@admin_required
def api_admin_update_order(order_id):
    data    = request.get_json(silent=True) or {}
    status  = data.get("status")
    allowed = {"pending", "paid", "completed", "cancelled"}
    if status not in allowed:
        return jsonify({"error": f"الحالات المتاحة: {sorted(allowed)}"}), 400

    order = get_order(order_id)
    if not order:
        return jsonify({"error": "الطلب غير موجود"}), 404

    update_order(order_id, status)

    # If completed, mark account sold and send credentials to buyer
    if status == "completed":
        update_account(order["account_id"], status="sold")
        _send_credentials_async(order)
    # If cancelled/rejected, restore account to available for resale
    elif status == "cancelled":
        update_account(order["account_id"], status="available")

    return jsonify({"success": True})


@app.route("/api/admin/upload", methods=["POST"])
@admin_required
def api_admin_upload():
    img = _save_upload(request.files.get("image"))
    if not img:
        return jsonify({"error": "لا توجد صورة صالحة"}), 400
    return jsonify({"success": True, "path": img, "url": _image_url(img)})


# ── Helpers ─────────────────────────────────────────────────
def _image_url(path: Optional[str]) -> str:
    if not path:
        return ""
    return f"/static/images/accounts/{os.path.basename(path)}"


def _format_account_public(a: dict) -> dict:
    return {
        "id":            a["id"],
        "name":          a["name"],
        "description":   a["description"],
        "price":         a["price"],
        "creation_year": a["creation_year"],
        "category":      a["category"],
        "image":         _image_url(a["image_path"]),
        "status":        a["status"],
        "followers":     a.get("followers", 0),
        "tweets_count":  a.get("tweets_count", 0),
        "features":      a.get("features", ""),
        "created_at":    a["created_at"],
    }


def _format_account(a: dict) -> dict:
    return {
        **_format_account_public(a),
        "email":      a.get("email", ""),
        "password":   a.get("password", ""),
        "updated_at": a["updated_at"],
    }


def _save_upload(file_storage) -> Optional[str]:
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    filename = f"{int(time.time())}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(filepath)
    return filepath


def _notify_admin_async(order_id, account, buyer_id, buyer_username) -> None:
    import threading, asyncio
    from config import BOT_TOKEN, ADMIN_ID, ADMIN_USERNAME

    if not BOT_TOKEN:
        return

    def _run():
        try:
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"admin_confirm_order_{order_id}"),
                InlineKeyboardButton("❌ رفض",         callback_data=f"admin_reject_order_{order_id}"),
            ]])
            msg = (
                f"🆕 <b>طلب جديد #{order_id}</b>\n\n"
                f"📦 {account['name']}\n"
                f"💰 ${account['price']:.2f}\n"
                f"👤 @{buyer_username} (ID: <code>{buyer_id}</code>)"
            )
            asyncio.run(Bot(BOT_TOKEN).send_message(
                chat_id=ADMIN_ID, text=msg, parse_mode="HTML",
                reply_markup=kb
            ))
        except Exception as exc:
            logger.warning(f"Admin notification failed: {exc}")

    threading.Thread(target=_run, daemon=True).start()


def _send_credentials_async(order: dict) -> None:
    import threading, asyncio
    from config import BOT_TOKEN, ADMIN_USERNAME

    if not BOT_TOKEN or not order.get("buyer_id"):
        return

    def _run():
        try:
            from telegram import Bot
            from database import get_account as _get_account
            acc = _get_account(order["account_id"])
            if not acc:
                return
            email    = acc.get("email") or "—"
            password = acc.get("password") or "—"
            features = acc.get("features") or ""
            msg = (
                f"🎉 <b>مبروك! تم تأكيد دفعك</b>\n\n"
                f"📦 الحساب: <b>{acc['name']}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔐 <b>بيانات دخول حسابك:</b>\n\n"
                f"📧 الإيميل:  <code>{email}</code>\n"
                f"🔑 الباسورد: <code>{password}</code>\n\n"
            )
            if features:
                msg += f"⭐ المميزات: {features}\n\n"
            msg += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📞 للدعم: <a href=\"https://t.me/{ADMIN_USERNAME}\">@{ADMIN_USERNAME}</a>\n\n"
                "✨ <i>شكراً لثقتك بنا!</i>"
            )
            asyncio.run(Bot(BOT_TOKEN).send_message(
                chat_id=order["buyer_id"], text=msg, parse_mode="HTML"
            ))
        except Exception as exc:
            logger.warning(f"Credentials delivery failed: {exc}")

    threading.Thread(target=_run, daemon=True).start()
