# auth_middleware.py
import hashlib
import hmac
import json
import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

ADMIN_ID = 8989271393
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData and return the parsed user dict,
    or None if validation fails.
    """
    try:
        params = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                from urllib.parse import unquote
                params[k] = unquote(v)

        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        user_str = params.get("user", "{}")
        return json.loads(user_str)
    except Exception as e:
        logger.warning(f"initData validation error: {e}")
        return None


def get_user_from_request() -> dict | None:
    """Extract and validate user from initData header or form field."""
    init_data = request.headers.get("X-Init-Data") or \
                request.form.get("initData") or \
                request.args.get("initData")

    if not init_data:
        # In dev/no-token mode, fall back to a header for testing
        return None

    if not BOT_TOKEN:
        # No token configured — cannot verify
        return None

    return verify_telegram_init_data(init_data)


def admin_required(f):
    """Decorator: blocks non-admin users with 403."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_from_request()
        if not user or int(user.get("id", 0)) != ADMIN_ID:
            logger.warning(
                f"Admin access denied for user: {user}"
            )
            return jsonify({
                "error": "Access Denied",
                "message": "You are not authorised to access this endpoint."
            }), 403
        return f(*args, **kwargs)
    return decorated
