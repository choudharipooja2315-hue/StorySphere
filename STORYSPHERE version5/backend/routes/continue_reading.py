from flask import Blueprint, request, jsonify, session
from database import mysql
from utils.decorators import login_required

continue_bp = Blueprint("continue", __name__)

# ======================================================
# SAVE / UPDATE READING PROGRESS
# ======================================================
@continue_bp.route("/api/continue-reading", methods=["POST"])
@login_required
def save_progress():

    data = request.get_json()

    story_id = data.get("story_id")
    chapter_id = data.get("chapter_id")

    if not story_id or not chapter_id:
        return jsonify({"error": "Missing data"}), 400

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        user_id = session["user_id"]

        cursor.execute("""
            INSERT INTO reading_progress (user_id, story_id, last_read_chapter_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                last_read_chapter_id = VALUES(last_read_chapter_id),
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, story_id, chapter_id))

        conn.commit()

        return jsonify({"message": "Progress saved"})

    except Exception as e:
        print("ERROR:", e)
        conn.rollback()
        return jsonify({"error": "Failed to save progress"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET CONTINUE READING LIST
# ======================================================
@continue_bp.route("/api/continue-reading", methods=["GET"])
@login_required
def get_continue_reading():

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        user_id = session["user_id"]

        cursor.execute("""
            SELECT 
                s.id,
                s.title,
                s.cover_image,
                rp.last_read_chapter_id
            FROM reading_progress rp
            JOIN stories s ON rp.story_id = s.id
            WHERE rp.user_id = %s
            ORDER BY rp.updated_at DESC
        """, (user_id,))

        rows = cursor.fetchall()

        result = [{
            "story_id": r[0],
            "title": r[1],
            "cover_image": r[2],
            "chapter_id": r[3]   # 👈 important for resume
        } for r in rows]

        return jsonify(result)

    except Exception as e:
        print("FETCH CONTINUE ERROR:", e)
        return jsonify({"error": "Failed to fetch continue reading"}), 500

    finally:
        cursor.close()
        conn.close()