from flask import Blueprint, request, jsonify, session
from database import mysql
from utils.decorators import login_required, writer_required
 
chapter_bp = Blueprint("chapter", __name__)
 
 
# =========================================================
# ❤️ LIKE / UNLIKE
# =========================================================
@chapter_bp.route("/api/chapter/<int:chapter_id>/like", methods=["POST"])
@login_required
def toggle_like(chapter_id):
 
    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()
 
    try:
        user_id = session.get("user_id")
 
        cursor.execute("""
            SELECT id FROM chapter_votes
            WHERE user_id=%s AND chapter_id=%s
        """, (user_id, chapter_id))
 
        existing = cursor.fetchone()
 
        if existing:
            cursor.execute("""
                DELETE FROM chapter_votes
                WHERE user_id=%s AND chapter_id=%s
            """, (user_id, chapter_id))
            liked = False
        else:
            cursor.execute("""
                INSERT INTO chapter_votes (user_id, chapter_id)
                VALUES (%s, %s)
            """, (user_id, chapter_id))
            liked = True
 
        cursor.execute("""
            SELECT COUNT(*) FROM chapter_votes
            WHERE chapter_id=%s
        """, (chapter_id,))
        count = cursor.fetchone()[0]
 
        conn.commit()
 
        return jsonify({
            "liked": liked,
            "likes_count": count
        })
 
    except Exception as e:
        print("LIKE ERROR:", e)
        conn.rollback()
        return jsonify({"error": "Like failed"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# 📖 GET SINGLE CHAPTER
# =========================================================
@chapter_bp.route("/api/chapter/<int:chapter_id>")
@login_required
def get_single_chapter(chapter_id):
 
    conn = mysql.connect()
    cursor = conn.cursor()
 
    try:
        user_id = session.get("user_id")
 
        cursor.execute("""
            SELECT id, title, content
            FROM chapters
            WHERE id=%s
        """, (chapter_id,))
        row = cursor.fetchone()
 
        if not row:
            return jsonify({"error": "Chapter not found"}), 404
 
        cursor.execute("""
            SELECT COUNT(*) FROM chapter_votes
            WHERE chapter_id=%s
        """, (chapter_id,))
        likes = cursor.fetchone()[0]
 
        cursor.execute("""
            SELECT id FROM chapter_votes
            WHERE chapter_id=%s AND user_id=%s
        """, (chapter_id, user_id))
        liked = cursor.fetchone() is not None
 
        return jsonify({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "likes": likes,
            "liked": liked
        })
 
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# 📚 GET READER STORY CHAPTERS
# =========================================================
@chapter_bp.route("/api/reader/story/<int:story_id>/chapters")
@login_required
def get_story_chapters(story_id):
 
    conn = mysql.connect()
    cursor = conn.cursor()
 
    try:
        cursor.execute("""
            SELECT
                c.id,
                c.title,
                COUNT(v.id) AS likes
            FROM chapters c
            LEFT JOIN chapter_votes v ON v.chapter_id = c.id
            WHERE c.story_id=%s AND c.status='published'
            GROUP BY c.id
            ORDER BY c.chapter_order ASC
        """, (story_id,))
 
        rows = cursor.fetchall()
 
        return jsonify([{
            "id": r[0],
            "title": r[1],
            "likes": r[2]
        } for r in rows])
 
    except Exception as e:
        print("CHAPTER LIST ERROR:", e)
        return jsonify({"error": "Failed to load chapters"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# 💬 ADD COMMENT
# FIX: column name is comment_text in schema, not comment
# =========================================================
@chapter_bp.route("/api/chapter/<int:chapter_id>/comment", methods=["POST"])
@login_required
def add_comment(chapter_id):
 
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
 
    comment_text = data.get("comment", "").strip()
 
    if not comment_text:
        return jsonify({"error": "Comment required"}), 400
 
    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()
 
    try:
        user_id = session.get("user_id")
 
        # FIX: column is comment_text, not comment
        cursor.execute("""
            INSERT INTO chapter_comments (user_id, chapter_id, comment_text)
            VALUES (%s, %s, %s)
        """, (user_id, chapter_id, comment_text))
 
        conn.commit()
 
        return jsonify({"message": "Comment added"})
 
    except Exception as e:
        print("COMMENT ERROR:", e)
        conn.rollback()
        return jsonify({"error": "Failed to add comment"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# 💬 GET COMMENTS
# FIX: column is comment_text in schema, not comment
# =========================================================
@chapter_bp.route("/api/chapter/<int:chapter_id>/comments")
@login_required
def get_comments(chapter_id):
 
    conn = mysql.connect()
    cursor = conn.cursor()
 
    try:
        # FIX: fetch c.comment_text, not c.comment
        cursor.execute("""
            SELECT u.username, c.comment_text
            FROM chapter_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.chapter_id=%s
            ORDER BY c.created_at DESC
        """, (chapter_id,))
 
        rows = cursor.fetchall()
 
        # Keep response key as "comment" so frontend requires no changes
        return jsonify([{
            "username": r[0],
            "comment": r[1]
        } for r in rows])
 
    except Exception as e:
        print("COMMENTS ERROR:", e)
        return jsonify({"error": "Failed to load comments"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# ✏️ CREATE CHAPTER (DRAFT)
# Route: POST /api/writer/story/<story_id>/chapter
# Called by ADD_CHAPTER.html → save() and publish()
# =========================================================
@chapter_bp.route("/api/writer/story/<int:story_id>/chapter", methods=["POST"])
@login_required
@writer_required
def create_chapter(story_id):
 
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
 
    title   = data.get("title", "").strip()
    content = data.get("content", "").strip()
 
    if not title:
        return jsonify({"error": "Title is required"}), 400
 
    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()
 
    try:
        # Verify this story belongs to the logged-in writer
        cursor.execute("""
            SELECT s.id FROM stories s
            JOIN writers w ON s.writer_id = w.id
            WHERE s.id=%s AND w.user_id=%s
        """, (story_id, session["user_id"]))
 
        if not cursor.fetchone():
            return jsonify({"error": "Unauthorized"}), 403
 
        # Determine next chapter_order
        cursor.execute("""
            SELECT COALESCE(MAX(chapter_order), 0) + 1
            FROM chapters
            WHERE story_id=%s
        """, (story_id,))
        next_order = cursor.fetchone()[0]
 
        cursor.execute("""
            INSERT INTO chapters (story_id, chapter_order, title, content, status)
            VALUES (%s, %s, %s, %s, 'draft')
        """, (story_id, next_order, title, content))
 
        chapter_id = cursor.lastrowid
        conn.commit()
 
        return jsonify({
            "message": "Chapter created",
            "chapter_id": chapter_id
        }), 201
 
    except Exception as e:
        conn.rollback()
        print("CREATE CHAPTER ERROR:", e)
        return jsonify({"error": "Failed to create chapter"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# ✏️ UPDATE CHAPTER (DRAFT EDIT)
# Route: PUT /api/writer/chapter/<chapter_id>
# Called by ADD_CHAPTER.html → save() when chapterId exists
# =========================================================
@chapter_bp.route("/api/writer/chapter/<int:chapter_id>", methods=["PUT"])
@login_required
@writer_required
def update_chapter(chapter_id):
 
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
 
    title   = data.get("title", "").strip()
    content = data.get("content", "").strip()
 
    if not title:
        return jsonify({"error": "Title is required"}), 400
 
    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()
 
    try:
        # Verify chapter belongs to this writer via join
        cursor.execute("""
            SELECT c.id FROM chapters c
            JOIN stories s ON c.story_id = s.id
            JOIN writers w ON s.writer_id = w.id
            WHERE c.id=%s AND w.user_id=%s
        """, (chapter_id, session["user_id"]))
 
        if not cursor.fetchone():
            return jsonify({"error": "Unauthorized"}), 403
 
        cursor.execute("""
            UPDATE chapters
            SET title=%s, content=%s
            WHERE id=%s
        """, (title, content, chapter_id))
 
        conn.commit()
 
        return jsonify({"message": "Chapter updated"})
 
    except Exception as e:
        conn.rollback()
        print("UPDATE CHAPTER ERROR:", e)
        return jsonify({"error": "Failed to update chapter"}), 500
 
    finally:
        cursor.close()
        conn.close()
 
 
# =========================================================
# 📢 PUBLISH CHAPTER
# Route: PUT /api/writer/chapter/<chapter_id>/publish
# Called by ADD_CHAPTER.html → publish() as final step
# =========================================================
@chapter_bp.route("/api/writer/chapter/<int:chapter_id>/publish", methods=["PUT"])
@login_required
@writer_required
def publish_chapter(chapter_id):
 
    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()
 
    try:
        # Verify chapter belongs to this writer
        cursor.execute("""
            SELECT c.id FROM chapters c
            JOIN stories s ON c.story_id = s.id
            JOIN writers w ON s.writer_id = w.id
            WHERE c.id=%s AND w.user_id=%s
        """, (chapter_id, session["user_id"]))
 
        if not cursor.fetchone():
            return jsonify({"error": "Unauthorized"}), 403
 
        cursor.execute("""
            UPDATE chapters
            SET status='published'
            WHERE id=%s
        """, (chapter_id,))
 
        conn.commit()
 
        return jsonify({"message": "Chapter published"})
 
    except Exception as e:
        conn.rollback()
        print("PUBLISH CHAPTER ERROR:", e)
        return jsonify({"error": "Failed to publish chapter"}), 500
 
    finally:
        cursor.close()
        conn.close()