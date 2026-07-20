# auth_middleware.py
import hashlib
import hmac
import json
import os
import logging
from functools import wraps
from urllib.parse import unquote
from flask import request, jsonify, session

logger = logging.getLogger(__name__)

ADMIN_ID  = int(os.environ.get("ADMIN_ID", "8989271393"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData HMAC and return the parsed user dict,
    or None if validation fails or token is missing.
    """
    if not BOT_TOKEN:
        return None
    try:
        params: dict[str, str] = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = unquote(v)

        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

        secret_key    = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            logger.warning("initData HMAC mismatch.")
            return None

        user_str = params.get("user", "{}")
        return json.loads(user_str)

    except Exception as e:
        logger.warning(f"initData validation error: {e}")
        return None


def get_user_from_request() -> dict | None:
    """Extract and validate user from X-Init-Data header, form field, or query param."""
    init_data = (
        request.headers.get("X-Init-Data")
        or request.form.get("initData")
        or request.args.get("initData")
    )
    if not init_data:
        return None
    return verify_telegram_init_data(init_data)


def is_session_admin() -> bool:
    """Check if the current Flask session belongs to an authenticated admin."""
    return bool(session.get("is_admin"))


def admin_required(f):
    """Decorator: allows access via valid Telegram initData OR authenticated browser session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1) Flask session (browser password login)
        if is_session_admin():
            return f(*args, **kwargs)

        # 2) Telegram WebApp initData
        user = get_user_from_request()
        if user and int(user.get("id", 0)) == ADMIN_ID:
            return f(*args, **kwargs)

        logger.warning(f"Admin access denied — user: {user}, session: {dict(session)}")
        return jsonify({
            "error": "Access Denied",
            "message": "You are not authorised. Please log in.",
            "code": "AUTH_REQUIRED"
        }), 403
    return decorated
