from flask import Blueprint, request, jsonify, session, current_app
from database import mysql
from werkzeug.utils import secure_filename
from utils.decorators import login_required, writer_required
import os

story_bp = Blueprint("story", __name__)


# ======================================================
# CREATE STORY
# ======================================================
@story_bp.route("/api/writer/stories", methods=["POST"])
@login_required
@writer_required
def create_story():

    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    language    = request.form.get("language", "").strip()
    audience    = request.form.get("audience", "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    cover    = request.files.get("cover_image")
    filename = None

    if cover and cover.filename:
        filename      = f"{session['user_id']}_{secure_filename(cover.filename)}"
        upload_folder = current_app.config["COVERS_FOLDER"]
        cover.save(os.path.join(upload_folder, filename))

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM writers WHERE user_id=%s",
                       (session["user_id"],))
        writer = cursor.fetchone()

        if not writer:
            return jsonify({"error": "Writer profile not found"}), 403

        writer_id = writer[0]

        cursor.execute("""
            INSERT INTO stories
            (writer_id, title, description, language,
             audience, cover_image, visibility, progress)
            VALUES (%s, %s, %s, %s, %s, %s, 'draft', 'ongoing')
        """, (writer_id, title, description, language, audience, filename))

        conn.commit()
        return jsonify({"message": "Story created successfully"}), 201

    except Exception as e:
        conn.rollback()
        print("CREATE STORY ERROR:", e)
        return jsonify({"error": "Failed to create story"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET WRITER STORIES
# ======================================================
@story_bp.route("/api/writer/stories", methods=["GET"])
@login_required
@writer_required
def get_writer_stories():

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM writers WHERE user_id=%s",
                       (session["user_id"],))
        writer = cursor.fetchone()

        if not writer:
            return jsonify({"error": "Writer not found"}), 403

        writer_id = writer[0]

        cursor.execute("""
            SELECT id, title, visibility, progress, cover_image
            FROM stories
            WHERE writer_id=%s
            ORDER BY created_at DESC
        """, (writer_id,))

        rows = cursor.fetchall()

        return jsonify([{
            "id":         r[0],
            "title":      r[1],
            "visibility": r[2],
            "progress":   r[3],
            "cover_image": r[4]
        } for r in rows])

    except Exception as e:
        print("GET WRITER STORIES ERROR:", e)
        return jsonify({"error": "Failed to fetch stories"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET SINGLE STORY WITH AUTHOR
# ======================================================
@story_bp.route("/api/stories/single/<int:story_id>")
@login_required
def get_single_story(story_id):

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                s.title,
                s.description,
                s.cover_image,
                w.user_id,
                w.pen_name,
                w.bio,
                w.profile_pic
            FROM stories s
            JOIN writers w ON s.writer_id = w.id
            WHERE s.id=%s
        """, (story_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Story not found"}), 404

        return jsonify({
            "title":       row[0],
            "description": row[1],
            "cover_image": row[2],
            "author": {
                "user_id":     row[3],
                "name":        row[4],
                "bio":         row[5],
                "profile_pic": row[6]
            }
        })

    except Exception as e:
        print("GET SINGLE STORY ERROR:", e)
        return jsonify({"error": "Failed to fetch story"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET READER CHAPTERS (published only)
# ======================================================
@story_bp.route("/api/reader/story/<int:story_id>/chapters")
@login_required
def get_reader_chapters(story_id):

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, title, chapter_order
            FROM chapters
            WHERE story_id=%s AND status='published'
            ORDER BY chapter_order ASC
        """, (story_id,))

        rows = cursor.fetchall()

        return jsonify([{
            "id":            r[0],
            "title":         r[1],
            "chapter_order": r[2]
        } for r in rows])

    except Exception as e:
        print("GET READER CHAPTERS ERROR:", e)
        return jsonify({"error": "Failed to load chapters"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET PUBLISHED STORIES
# ======================================================
@story_bp.route("/api/stories/published")
def get_published_stories():

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, title, cover_image, progress
            FROM stories
            WHERE visibility='published'
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

        return jsonify([{
            "id":          r[0],
            "title":       r[1],
            "cover_image": r[2],
            "progress":    r[3]
        } for r in rows])

    except Exception as e:
        print("GET PUBLISHED STORIES ERROR:", e)
        return jsonify({"error": "Failed to fetch stories"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# PUBLISH STORY
# ======================================================
@story_bp.route("/api/stories/publish/<int:story_id>", methods=["PUT"])
@login_required
@writer_required
def publish_story(story_id):

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE stories s
            JOIN writers w ON s.writer_id = w.id
            SET s.visibility='published'
            WHERE s.id=%s AND w.user_id=%s
        """, (story_id, session["user_id"]))

        if cursor.rowcount == 0:
            return jsonify({"error": "Unauthorized"}), 403

        conn.commit()
        return jsonify({"message": "Story published successfully"})

    except Exception as e:
        conn.rollback()
        print("PUBLISH STORY ERROR:", e)
        return jsonify({"error": "Failed to publish story"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# DELETE STORY
# ======================================================
@story_bp.route("/api/writer/stories/<int:story_id>", methods=["DELETE"])
@login_required
@writer_required
def delete_story(story_id):

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE s FROM stories s
            JOIN writers w ON s.writer_id = w.id
            WHERE s.id=%s AND w.user_id=%s
        """, (story_id, session["user_id"]))

        if cursor.rowcount == 0:
            return jsonify({"error": "Unauthorized"}), 403

        conn.commit()
        return jsonify({"message": "Story deleted successfully"})

    except Exception as e:
        conn.rollback()
        print("DELETE STORY ERROR:", e)
        return jsonify({"error": "Failed to delete story"}), 500

    finally:
        cursor.close()
        conn.close()


# ======================================================
# GET WRITER CHAPTERS (all statuses, with stats)
# FIX: chapter_likes → chapter_votes (table does not exist in schema)
# ======================================================
@story_bp.route("/api/writer/story/<int:story_id>/chapters")
@login_required
@writer_required
def get_writer_chapters(story_id):

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                c.id,
                c.title,
                c.status,
                c.chapter_order,
                COUNT(DISTINCT v.id),
                COUNT(DISTINCT cm.id)
            FROM chapters c
            LEFT JOIN chapter_votes v  ON v.chapter_id  = c.id
            LEFT JOIN chapter_comments cm ON cm.chapter_id = c.id
            WHERE c.story_id=%s
            GROUP BY c.id, c.title, c.status, c.chapter_order
            ORDER BY c.chapter_order ASC
        """, (story_id,))

        rows = cursor.fetchall()

        return jsonify([{
            "id":            r[0],
            "title":         r[1],
            "status":        r[2],
            "chapter_order": r[3],
            "likes":         r[4],
            "comments":      r[5]
        } for r in rows])

    except Exception as e:
        print("GET WRITER CHAPTERS ERROR:", e)
        return jsonify({"error": "Failed to load chapters"}), 500

    finally:
        cursor.close()
        conn.close()