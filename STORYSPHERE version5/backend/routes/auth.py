from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import mysql
import re
import traceback

auth_bp = Blueprint("auth", __name__)

# =====================================================
# VALIDATION
# =====================================================

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def is_valid_username(username):
    return re.match(r'^[a-zA-Z0-9_]{3,50}$', username)

def is_strong_password(password):
    return len(password) >= 8


# =====================================================
# REGISTER
# =====================================================

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if not is_valid_username(username):
        return jsonify({"error": "Invalid username format"}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    if not is_strong_password(password):
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    hashed_password = generate_password_hash(password)

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM users WHERE username=%s OR email=%s",
            (username, email)
        )
        if cursor.fetchone():
            return jsonify({"error": "Username or email already exists"}), 400

        cursor.execute("""
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
        """, (username, email, hashed_password))

        conn.commit()
        return jsonify({"message": "Registration successful"}), 201

    except Exception as e:
        print(f"Registration Error: {e}")
        conn.rollback()
        return jsonify({"error": "Registration failed"}), 500

    finally:
        cursor.close()
        conn.close()


# =====================================================
# LOGIN
# =====================================================

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username_input = data.get("username", "").strip()
    password = data.get("password", "")

    if not username_input or not password:
        return jsonify({"error": "Username/email and password required"}), 400

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        # We fetch id, username, password, and profile_pic (added in your schema later)
        cursor.execute("""
            SELECT id, username, password
            FROM users
            WHERE username=%s OR email=%s
            LIMIT 1
        """, (username_input, username_input))

        user = cursor.fetchone()

        if not user or not check_password_hash(user[2], password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Check if user is a writer
        cursor.execute("SELECT id FROM writers WHERE user_id=%s", (user[0],))
        writer = cursor.fetchone()
        
        is_writer = True if writer else False

        # Session Setup
        session.clear()
        session["user_id"] = user[0]
        session["username"] = user[1]
        session["is_writer"] = is_writer
        session.permanent = True 

        return jsonify({
            "message": "Login successful",
            "is_writer": is_writer,
            "username": user[1]
        }), 200

    except Exception as e:
        # This will show you exactly what is wrong in your terminal
        print("--- LOGIN ERROR ---")
        traceback.print_exc() 
        return jsonify({"error": "Login failed due to server error"}), 500

    finally:
        cursor.close()
        conn.close()


# =====================================================
# GET CURRENT USER
# =====================================================

@auth_bp.route("/api/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "user_id": session["user_id"],
        "username": session["username"],
        "is_writer": session.get("is_writer", False)
    }), 200


# =====================================================
# LOGOUT
# =====================================================

@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200