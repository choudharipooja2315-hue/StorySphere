from functools import wraps
from flask import session, jsonify

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 🔥 Check if user_id exists in the session
        if "user_id" not in session:
            # We return a 401. The Frontend should check for this status code.
            return jsonify({
                "error": "Authentication required",
                "status": "unauthorized"
            }), 401
        return f(*args, **kwargs)
    return wrapper


def writer_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 1. Check if logged in
        if "user_id" not in session:
            return jsonify({
                "error": "Authentication required",
                "status": "unauthorized"
            }), 401

        # 2. Check if the user is actually a writer
        if not session.get("is_writer"):
            return jsonify({
                "error": "Writer access required",
                "status": "forbidden"
            }), 403

        return f(*args, **kwargs)
    return wrapper


def active_user_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Ensure user is logged in first
        if "user_id" not in session:
            return jsonify({
                "error": "Authentication required",
                "status": "unauthorized"
            }), 401

        # Logic for deactivated accounts
        if not session.get("is_active", True):
            return jsonify({
                "error": "Account inactive",
                "status": "forbidden"
            }), 403

        return f(*args, **kwargs)
    return wrapper