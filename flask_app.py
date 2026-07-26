# flask_app.py — Complete marketplace API with mini app routes
import os
import time
import logging
import json as _json
from typing import Optional, Dict, List
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, send_from_directory, session, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from auth_middleware import admin_required, is_session_admin, get_user_from_request
from database import (
    get_or_create_user, get_user, update_user, get_user_by_telegram_id,
    get_all_accounts, get_all_accounts_admin, get_account,
    add_account, update_account, delete_account,
    get_all_orders, get_pending_orders, update_order, get_stats,
    create_order, get_order,
    get_or_create_chat, send_message, get_messages,
    get_marketplace_stats,
)
from config import ADMIN_ID, ADMIN_PASSWORD, get_payment_methods, calculate_commission

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "static/images/accounts"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov"}

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-me-in-prod-123!")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
CORS(app, resources={r"/api/*": {"origins": "*"}})

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# HEALTH & STATUS
# ============================================================

@app.route("/health")
@app.route("/ping")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route("/")
def index():
    """Main marketplace page."""
    from config import MARKETPLACE_NAME
    return render_template("index.html", marketplace_name=MARKETPLACE_NAME)


@app.route("/admin")
def admin():
    """Admin dashboard."""
    return render_template("admin.html")


@app.route("/seller")
def seller_dashboard():
    """Seller dashboard."""
    return render_template("seller.html")


# ============================================================
# AUTHENTICATION
# ============================================================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Admin login with password."""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()
    
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        session.permanent = True
        return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح"})
    
    return jsonify({"success": False, "error": "كلمة المرور غير صحيحة"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """Logout."""
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/check", methods=["GET"])
def api_auth_check():
    """Check authentication status."""
    if is_session_admin():
        return jsonify({"authed": True, "via": "session"})
    
    user = get_user_from_request()
    if user and int(user.get("id", 0)) == ADMIN_ID:
        return jsonify({"authed": True, "via": "telegram"})
    
    return jsonify({"authed": False}), 403


@app.route("/api/auth/telegram", methods=["POST"])
def api_telegram_auth():
    """Authenticate with Telegram initData."""
    data = request.get_json(silent=True) or {}
    init_data = data.get("initData", "")
    
    if not init_data:
        return jsonify({"success": False, "error": "No initData provided"}), 400
    
    try:
        # Parse Telegram initData
        params = dict(p.split("=", 1) for p in init_data.split("&") if "=" in p)
        user_data = _json.loads(__import__("urllib.parse").unquote(params.get("user", "{}")))
        
        telegram_id = user_data.get("id")
        if not telegram_id:
            return jsonify({"success": False, "error": "Invalid user data"}), 400
        
        # Get or create user
        user = get_or_create_user(
            telegram_id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name")
        )
        
        return jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "telegram_id": user["telegram_id"],
                "username": user["username"],
                "first_name": user["first_name"]
            }
        })
    
    except Exception as e:
        logger.error(f"Telegram auth error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PUBLIC LISTINGS API
# ============================================================

@app.route("/api/listings", methods=["GET"])
def api_get_listings():
    """Get all available listings."""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    offset = (page - 1) * limit
    
    listings = get_all_accounts(status="available")
    total = len(listings)
    paginated = listings[offset:offset + limit]
    
    return jsonify({
        "listings": [_format_listing_public(l) for l in paginated],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    })


@app.route("/api/listings/<int:listing_id>", methods=["GET"])
def api_get_listing(listing_id):
    """Get listing details."""
    listing = get_account(listing_id)
    if not listing:
        return jsonify({"success": False, "error": "Listing not found"}), 404
    
    return jsonify({
        "success": True,
        "listing": _format_listing_public(listing)
    })


@app.route("/api/listings/search", methods=["GET"])
def api_search_listings():
    """Search listings."""
    query = request.args.get("q", "").lower()
    category = request.args.get("category", "")
    
    listings = get_all_accounts(status="available")
    
    # Simple filter
    if query:
        listings = [l for l in listings if query in l["name"].lower() or query in (l.get("description") or "").lower()]
    if category:
        listings = [l for l in listings if l.get("category") == category]
    
    return jsonify({"listings": [_format_listing_public(l) for l in listings]})


# ============================================================
# USER PROFILE API
# ============================================================

@app.route("/api/users/<int:user_id>", methods=["GET"])
def api_get_user(user_id):
    """Get user profile."""
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    return jsonify({
        "success": True,
        "user": _format_user_public(user)
    })


@app.route("/api/me", methods=["GET"])
def api_get_current_user():
    """Get current user profile."""
    user_data = get_user_from_request()
    if not user_data:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    user = get_user(user_data.get("id"))
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    return jsonify({"success": True, "user": _format_user_full(user)})


@app.route("/api/me", methods=["PUT"])
def api_update_current_user():
    """Update current user profile."""
    user_data = get_user_from_request()
    if not user_data:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    data = request.get_json(silent=True) or {}
    
    update_user(user_data["id"], **{
        "bio": data.get("bio"),
        "language": data.get("language"),
        "currency": data.get("currency"),
        "notification_enabled": data.get("notification_enabled", True)
    })
    
    user = get_user(user_data["id"])
    return jsonify({"success": True, "user": _format_user_full(user)})


# ============================================================
# ORDERS API
# ============================================================

@app.route("/api/orders", methods=["POST"])
def api_create_order():
    """Create a new order."""
    data = request.get_json(silent=True) or {}
    listing_id = data.get("listing_id")
    payment_method = data.get("payment_method", "stars")
    
    if not listing_id:
        return jsonify({"success": False, "error": "listing_id is required"}), 400
    
    listing = get_account(listing_id)
    if not listing:
        return jsonify({"success": False, "error": "Listing not found"}), 404
    
    if listing["status"] != "available":
        return jsonify({"success": False, "error": "Listing not available"}), 409
    
    user_data = get_user_from_request()
    buyer_id = user_data.get("id") if user_data else 0
    
    # Calculate commission
    commission_info = calculate_commission(listing["price"])
    
    order_id = create_order(
        listing_id=listing_id,
        buyer_id=buyer_id,
        seller_id=listing["seller_id"],
        amount=listing["price"],
        currency=listing.get("currency", "USD"),
        payment_method=payment_method
    )
    
    # Update listing status to reserved
    update_account(listing_id, status="reserved")
    
    return jsonify({
        "success": True,
        "order_id": order_id,
        "listing": _format_listing_public(listing),
        "commission": commission_info,
        "payment_methods": get_payment_methods()
    }), 201


@app.route("/api/orders/<int:order_id>", methods=["GET"])
def api_get_order(order_id):
    """Get order details."""
    order = get_order(order_id)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    
    return jsonify({"success": True, "order": _format_order(order)})


@app.route("/api/orders/<int:order_id>/confirm", methods=["POST"])
def api_confirm_order(order_id):
    """Confirm order received."""
    order = get_order(order_id)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    
    update_order(order_id, status="completed")
    update_account(order["account_id"], status="sold")
    
    return jsonify({"success": True, "message": "Order confirmed"})


# ============================================================
# CHATS API
# ============================================================

@app.route("/api/chats", methods=["GET"])
def api_get_chats():
    """Get user's chats."""
    user_data = get_user_from_request()
    if not user_data:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    # TODO: Implement chat list from database
    return jsonify({"success": True, "chats": []})


@app.route("/api/chats/<int:chat_id>/messages", methods=["GET"])
def api_get_chat_messages(chat_id):
    """Get messages in a chat."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    messages = get_messages(chat_id, limit=limit, offset=offset)
    
    return jsonify({
        "success": True,
        "messages": [_format_message(m) for m in messages]
    })


@app.route("/api/chats/<int:chat_id>/messages", methods=["POST"])
def api_send_message(chat_id):
    """Send a message."""
    user_data = get_user_from_request()
    if not user_data:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    receiver_id = data.get("receiver_id")
    
    if not content or not receiver_id:
        return jsonify({"success": False, "error": "Missing fields"}), 400
    
    message_id = send_message(
        chat_id=chat_id,
        sender_id=user_data["id"],
        receiver_id=receiver_id,
        content=content,
        message_type="text"
    )
    
    return jsonify({
        "success": True,
        "message_id": message_id
    }), 201


# ============================================================
# STATS & MARKETPLACE INFO
# ============================================================

@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    """Get marketplace statistics."""
    stats = get_marketplace_stats()
    return jsonify({"success": True, "stats": stats})


@app.route("/api/info", methods=["GET"])
def api_get_info():
    """Get marketplace information."""
    from config import MARKETPLACE_NAME, get_payment_info
    
    return jsonify({
        "success": True,
        "marketplace": {
            "name": MARKETPLACE_NAME,
            "payment_info": get_payment_info(),
            "stats": get_marketplace_stats()
        }
    })


# ============================================================
# ADMIN API
# ============================================================

@app.route("/api/admin/listings", methods=["GET"])
@admin_required
def api_admin_get_listings():
    """Get all listings for admin."""
    listings = get_all_accounts_admin()
    return jsonify({"success": True, "listings": [_format_listing_admin(l) for l in listings]})


@app.route("/api/admin/listings", methods=["POST"])
@admin_required
def api_admin_create_listing():
    """Admin create listing."""
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    
    try:
        price = float(request.form.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid price"}), 400
    
    image_path = _save_upload(request.files.get("image"))
    
    listing_id = add_account(
        name=name,
        description=request.form.get("description", ""),
        price=price,
        category=request.form.get("category", "other"),
        image_path=image_path,
        email=request.form.get("email", ""),
        password=request.form.get("password", ""),
        followers=int(request.form.get("followers", 0) or 0),
        tweets_count=int(request.form.get("tweets_count", 0) or 0),
        features=request.form.get("features", "")
    )
    
    return jsonify({"success": True, "listing_id": listing_id}), 201


@app.route("/api/admin/listings/<int:listing_id>", methods=["PUT"])
@admin_required
def api_admin_update_listing(listing_id):
    """Admin update listing."""
    if not get_account(listing_id):
        return jsonify({"success": False, "error": "Listing not found"}), 404
    
    updates = {}
    for field in ["name", "description", "status", "category"]:
        if field in request.form:
            updates[field] = request.form[field]
    
    if "price" in request.form:
        try:
            updates["price"] = float(request.form["price"])
        except (ValueError, TypeError):
            pass
    
    img = _save_upload(request.files.get("image"))
    if img:
        updates["image_path"] = img
    
    update_account(listing_id, **updates)
    return jsonify({"success": True})


@app.route("/api/admin/listings/<int:listing_id>", methods=["DELETE"])
@admin_required
def api_admin_delete_listing(listing_id):
    """Admin delete listing."""
    if not get_account(listing_id):
        return jsonify({"success": False, "error": "Listing not found"}), 404
    
    delete_account(listing_id)
    return jsonify({"success": True})


# ============================================================
# HELPERS
# ============================================================

def _image_url(path: Optional[str]) -> str:
    """Get image URL from path."""
    if not path:
        return ""
    return f"/static/images/accounts/{os.path.basename(path)}"


def _format_listing_public(listing: dict) -> dict:
    """Format listing for public view."""
    return {
        "id": listing["id"],
        "title": listing["name"],
        "description": listing.get("description", ""),
        "price": listing["price"],
        "currency": listing.get("currency", "USD"),
        "category": listing.get("category", ""),
        "image": _image_url(listing.get("image_path")),
        "status": listing.get("status", "available"),
        "created_at": listing.get("created_at"),
        "updated_at": listing.get("updated_at")
    }


def _format_listing_admin(listing: dict) -> dict:
    """Format listing for admin view."""
    public = _format_listing_public(listing)
    return {
        **public,
        "email": listing.get("email", ""),
        "password": listing.get("password", ""),
        "seller_id": listing.get("seller_id")
    }


def _format_user_public(user: dict) -> dict:
    """Format user for public view."""
    return {
        "id": user["id"],
        "username": user.get("username"),
        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "bio": user.get("bio", ""),
        "avatar": user.get("avatar_url"),
        "rating": user.get("rating", 5.0),
        "followers": user.get("followers", 0),
        "is_verified": user.get("is_verified", False)
    }


def _format_user_full(user: dict) -> dict:
    """Format user for full view."""
    public = _format_user_public(user)
    return {
        **public,
        "email": user.get("email"),
        "language": user.get("language", "en"),
        "currency": user.get("currency", "USD"),
        "completed_sales": user.get("completed_sales", 0),
        "completed_purchases": user.get("completed_purchases", 0),
        "created_at": user.get("created_at")
    }


def _format_order(order: dict) -> dict:
    """Format order."""
    return {
        "id": order["id"],
        "listing_id": order.get("listing_id"),
        "buyer_id": order.get("buyer_id"),
        "seller_id": order.get("seller_id"),
        "status": order.get("status", "pending"),
        "amount": order.get("amount"),
        "currency": order.get("currency", "USD"),
        "payment_method": order.get("payment_method"),
        "created_at": order.get("created_at"),
        "paid_at": order.get("paid_at"),
        "completed_at": order.get("completed_at")
    }


def _format_message(message: dict) -> dict:
    """Format message."""
    return {
        "id": message["id"],
        "sender_id": message.get("sender_id"),
        "content": message.get("content"),
        "type": message.get("message_type", "text"),
        "is_read": message.get("is_read", False),
        "created_at": message.get("created_at"),
        "read_at": message.get("read_at")
    }


def _save_upload(file_storage) -> Optional[str]:
    """Save uploaded file."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    
    filename = secure_filename(file_storage.filename)
    filename = f"{int(time.time())}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(filepath)
    
    return filepath


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"success": False, "error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"Server error: {error}")
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=False)
