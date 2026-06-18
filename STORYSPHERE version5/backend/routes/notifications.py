from flask import Blueprint, jsonify, session
from database import mysql
from utils.decorators import login_required

notifications_bp = Blueprint("notifications", __name__)


# ======================================================
# GET NOTIFICATIONS
# ======================================================
@notifications_bp.route("/api/notifications")
@login_required
def get_notifications():

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT message, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))

        rows = cursor.fetchall()

        return jsonify([{
            "message": r[0],
            "created_at": str(r[1])
        } for r in rows])

    finally:
        cursor.close()
        conn.close()