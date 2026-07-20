# flask_app.py
import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from auth_middleware import admin_required
from database import (
    get_all_accounts, get_all_accounts_admin, get_account,
    add_account, update_account, delete_account,
    get_all_orders, update_order, get_stats
)

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "static/images/accounts"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Page routes ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ── Public API ───────────────────────────────────────────

@app.route("/api/accounts", methods=["GET"])
def api_get_accounts():
    accounts = get_all_accounts(status="available")
    result = []
    for a in accounts:
        result.append({
            "id": a["id"],
            "name": a["name"],
            "description": a["description"],
            "price": a["price"],
            "creation_year": a["creation_year"],
            "category": a["category"],
            "image": _image_url(a["image_path"]),
            "status": a["status"],
            "created_at": a["created_at"],
        })
    return jsonify(result)


@app.route("/api/accounts/<int:account_id>", methods=["GET"])
def api_get_account(account_id):
    a = get_account(account_id)
    if not a:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id": a["id"],
        "name": a["name"],
        "description": a["description"],
        "price": a["price"],
        "creation_year": a["creation_year"],
        "category": a["category"],
        "image": _image_url(a["image_path"]),
        "status": a["status"],
        "created_at": a["created_at"],
    })


# ── Public Buy ────────────────────────────────────────

@app.route("/api/buy", methods=["POST"])
def api_buy():
    """Public endpoint — any Telegram user can place an order."""
    from database import create_order, update_account, get_account
    import os

    acc_id_raw = request.form.get("account_id") or (request.get_json(silent=True) or {}).get("account_id")
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

    # Extract buyer info from initData if present (best-effort)
    buyer_id       = 0
    buyer_username = "unknown"
    init_data_raw  = request.form.get("initData") or request.headers.get("X-Init-Data", "")
    if init_data_raw:
        try:
            from urllib.parse import unquote
            import json as _json
            params = dict(p.split("=", 1) for p in init_data_raw.split("&") if "=" in p)
            user   = _json.loads(unquote(params.get("user", "{}")))
            buyer_id       = user.get("id", 0)
            buyer_username = user.get("username", "unknown")
        except Exception:
            pass

    order_id = create_order(acc_id, buyer_id, buyer_username)
    update_account(acc_id, status="reserved")

    # Notify admin via bot (best-effort, non-blocking)
    try:
        import asyncio, threading
        from config import BOT_TOKEN, ADMIN_ID
        if BOT_TOKEN:
            from telegram import Bot
            msg = (
                f"🆕 *New Order #{order_id}*\n\n"
                f"📦 {account['name']}\n"
                f"💰 ${account['price']:.2f}\n"
                f"👤 @{buyer_username} (ID: `{buyer_id}`)"
            )
            def _notify():
                asyncio.run(Bot(BOT_TOKEN).send_message(
                    chat_id=ADMIN_ID, text=msg, parse_mode="Markdown"
                ))
            threading.Thread(target=_notify, daemon=True).start()
    except Exception as exc:
        logger.warning(f"Admin notification failed: {exc}")

    return jsonify({
        "success":      True,
        "order_id":     order_id,
        "account_name": account["name"],
        "price":        account["price"],
    })


# ── Admin API ─────────────────────────────────────────────

@app.route("/api/admin/accounts", methods=["GET"])
@admin_required
def api_admin_get_accounts():
    accounts = get_all_accounts_admin()
    return jsonify([_format_account(a) for a in accounts])


@app.route("/api/admin/accounts", methods=["POST"])
@admin_required
def api_admin_create_account():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    price = float(request.form.get("price", 0))
    description = request.form.get("description", "")
    creation_year = request.form.get("creation_year")
    creation_year = int(creation_year) if creation_year else None
    category = request.form.get("category", "twitter")

    image_path = _save_upload(request.files.get("image"))

    account_id = add_account(name, description, price, creation_year,
                             category, image_path)
    return jsonify({"success": True, "id": account_id}), 201


@app.route("/api/admin/accounts/<int:account_id>", methods=["PUT"])
@admin_required
def api_admin_update_account(account_id):
    if not get_account(account_id):
        return jsonify({"error": "Not found"}), 404

    updates = {}
    for field in ["name", "description", "status", "category"]:
        if field in request.form:
            updates[field] = request.form[field]
    if "price" in request.form:
        updates["price"] = float(request.form["price"])
    if "creation_year" in request.form and request.form["creation_year"]:
        updates["creation_year"] = int(request.form["creation_year"])

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
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed = {"pending", "paid", "completed", "cancelled"}
    if status not in allowed:
        return jsonify({"error": f"Invalid status. Allowed: {allowed}"}), 400
    update_order(order_id, status)
    return jsonify({"success": True})


@app.route("/api/admin/upload", methods=["POST"])
@admin_required
def api_admin_upload():
    img = _save_upload(request.files.get("image"))
    if not img:
        return jsonify({"error": "No valid image uploaded"}), 400
    return jsonify({"success": True, "path": img, "url": _image_url(img)})


# ── Helpers ───────────────────────────────────────────────

def _image_url(path):
    if not path:
        return ""
    filename = os.path.basename(path)
    return f"/static/images/accounts/{filename}"


def _format_account(a):
    return {
        "id": a["id"],
        "name": a["name"],
        "description": a["description"],
        "price": a["price"],
        "creation_year": a["creation_year"],
        "category": a["category"],
        "image": _image_url(a["image_path"]),
        "status": a["status"],
        "created_at": a["created_at"],
        "updated_at": a["updated_at"],
    }


def _save_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    # Prepend timestamp to avoid collisions
    import time
    filename = f"{int(time.time())}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(filepath)
    return filepath
