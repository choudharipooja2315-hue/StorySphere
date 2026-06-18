from flask import Blueprint, request, jsonify, session
from database import mysql
from utils.decorators import login_required
import traceback

reader_bp = Blueprint("reader", __name__)


# ======================================================
# NEW ARRIVALS
# ======================================================
@reader_bp.route("/api/stories")
@login_required
def get_stories():

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                s.id, s.title, s.cover_image, s.progress, w.pen_name
            FROM stories s
            JOIN writers w ON s.writer_id = w.id
            WHERE s.visibility='published'
            ORDER BY s.created_at DESC
        """)
        rows = cursor.fetchall()

        return jsonify([{
            "id":          r[0],
            "title":       r[1],
            "cover_image": r[2],
            "progress":    r[3],
            "author":      r[4]
        } for r in rows])

    except Exception as e:
        print(f"GET STORIES ERROR: {e}")
        return jsonify({"error": "Failed to load stories"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# FOLLOW / UNFOLLOW
# ======================================================
@reader_bp.route("/api/follow", methods=["POST"])
@login_required
def follow_writer():

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    writer_user_id = data.get("writer_id")

    if not writer_user_id:
        return jsonify({"error": "Writer ID missing"}), 400

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:
        user_id = session["user_id"]

        # Map user_id → writer_id
        cursor.execute("SELECT id FROM writers WHERE user_id=%s", (writer_user_id,))
        writer = cursor.fetchone()
        if not writer:
            return jsonify({"error": "Writer not found"}), 404

        writer_id = writer[0]

        cursor.execute("""
            SELECT id FROM writer_followers
            WHERE follower_user_id=%s AND writer_id=%s
        """, (user_id, writer_id))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                DELETE FROM writer_followers
                WHERE follower_user_id=%s AND writer_id=%s
            """, (user_id, writer_id))
            conn.commit()
            return jsonify({"followed": False})
        else:
            cursor.execute("""
                INSERT INTO writer_followers (follower_user_id, writer_id)
                VALUES (%s, %s)
            """, (user_id, writer_id))
            conn.commit()
            return jsonify({"followed": True})

    except Exception as e:
        print("FOLLOW ERROR:")
        traceback.print_exc()
        conn.rollback()
        return jsonify({"error": "Follow failed"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# LIBRARY (GET + ADD)
# FIX: table was 'library' — schema defines it as 'reader_bookmarks'
# ======================================================
@reader_bp.route("/api/library", methods=["GET", "POST"])
@login_required
def library_handler():

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:
        user_id = session["user_id"]

        # =========================
        # GET LIBRARY
        # =========================
        if request.method == "GET":

            # FIX: FROM library → FROM reader_bookmarks
            cursor.execute("""
                SELECT
                    s.id,
                    s.title,
                    s.cover_image
                FROM reader_bookmarks rb
                JOIN stories s ON rb.story_id = s.id
                WHERE rb.user_id = %s
                ORDER BY rb.created_at DESC
            """, (user_id,))

            rows = cursor.fetchall()

            return jsonify([{
                "id":          r[0],
                "title":       r[1],
                "cover_image": r[2]
            } for r in rows])

        # =========================
        # ADD TO LIBRARY
        # =========================
        if request.method == "POST":

            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid JSON"}), 400

            story_id = data.get("story_id")

            if not story_id:
                return jsonify({"error": "Story ID required"}), 400

            # FIX: SELECT/INSERT into reader_bookmarks, not library
            cursor.execute("""
                SELECT id FROM reader_bookmarks
                WHERE user_id=%s AND story_id=%s
            """, (user_id, story_id))

            if cursor.fetchone():
                return jsonify({"message": "Already added"})

            cursor.execute("""
                INSERT INTO reader_bookmarks (user_id, story_id)
                VALUES (%s, %s)
            """, (user_id, story_id))

            conn.commit()

            return jsonify({"message": "Added to library"})

    except Exception as e:
        print("LIBRARY ERROR:", e)
        conn.rollback()
        return jsonify({"error": "Failed"}), 500

    finally:
        cursor.close()
        conn.close()