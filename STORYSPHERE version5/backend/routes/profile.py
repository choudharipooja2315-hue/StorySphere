from flask import Blueprint, request, jsonify, session, current_app
from database import mysql
import os

profile_bp = Blueprint("profile", __name__)


# =====================================================
# GET PROFILE DATA
# FIX Bug 4: 'about' column does not exist on users table.
#            Removed it from SELECT — only username and profile_pic exist.
# =====================================================

@profile_bp.route("/api/profile", methods=["GET"])
def get_profile():

    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        # FIX: removed 'about' — it is not in the users schema
        cursor.execute("""
            SELECT username, profile_pic
            FROM users
            WHERE id=%s
        """, (session["user_id"],))

        row = cursor.fetchone()

        if not row:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "username":    row[0],
            "profile_pic": row[1]   # may be NULL
        })

    except Exception as e:
        print("GET PROFILE ERROR:", e)
        return jsonify({"error": "Failed to load profile"}), 500

    finally:
        cursor.close()
        conn.close()


# =====================================================
# UPDATE PROFILE (PROFILE PIC ONLY)
# FIX Bug 4: removed all SET about=... — column doesn't exist.
# FIX Bug 7: profile pics are saved to 'profile_pics/' subfolder.
#            WRITER_DASHBOARD was loading from '/uploads/profiles/'
#            (wrong). The correct serve path is '/uploads/profile_pics/'.
#            The filename stored in DB is just the bare filename;
#            the frontend must prefix it with /uploads/profile_pics/.
# =====================================================

@profile_bp.route("/api/profile/update", methods=["POST"])
def update_profile():

    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    file = request.files.get("profile_pic")

    conn = mysql.connect()
    conn.autocommit(False)
    cursor = conn.cursor()

    try:

        if file and file.filename != "":

            filename = f"user_{session['user_id']}.jpg"

            # FIX Bug 7: folder key is PROFILE_FOLDER → saves to profile_pics/
            save_path = os.path.join(
                current_app.config["PROFILE_FOLDER"],
                filename
            )

            file.save(save_path)

            # FIX: removed about=%s — column doesn't exist
            cursor.execute("""
                UPDATE users
                SET profile_pic=%s
                WHERE id=%s
            """, (filename, session["user_id"]))

            conn.commit()

            return jsonify({
                "message":     "Profile updated",
                "profile_pic": filename
            })

        else:
            # No file sent — nothing to update
            return jsonify({"message": "No changes made"})

    except Exception as e:
        conn.rollback()
        print("UPDATE PROFILE ERROR:", e)
        return jsonify({"error": "Profile update failed"}), 500

    finally:
        cursor.close()
        conn.close()