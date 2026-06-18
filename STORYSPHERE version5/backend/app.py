from flask import Flask, send_from_directory, session, redirect
from flask_cors import CORS
import os
from database import init_db

# =========================================================
# CREATE APP
# =========================================================

app = Flask(
    __name__,
    static_folder="../ASSETS",
    static_url_path="/ASSETS"
)

# =========================================================
# SESSION CONFIG
# =========================================================

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    SESSION_PERMANENT=True
)

# =========================================================
# CORS CONFIG
# =========================================================

CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
        "http://127.0.0.1:5502",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://localhost:5502"
    ]
)

# =========================================================
# PATH SETUP
# =========================================================

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

ROOT_PATH    = PROJECT_ROOT
READERS_PATH = os.path.join(PROJECT_ROOT, "readers")
UPLOAD_ROOT  = os.path.join(BASE_DIR, "uploads")

# =========================================================
# UPLOAD FOLDERS
# =========================================================

COVERS_FOLDER  = os.path.join(UPLOAD_ROOT, "covers")
PROFILE_FOLDER = os.path.join(UPLOAD_ROOT, "profile_pics")

os.makedirs(COVERS_FOLDER,  exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)

app.config["COVERS_FOLDER"]  = COVERS_FOLDER
app.config["PROFILE_FOLDER"] = PROFILE_FOLDER

# =========================================================
# INIT DATABASE
# =========================================================

init_db(app)

# =========================================================
# REGISTER BLUEPRINTS
# =========================================================

from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.story import story_bp
from routes.chapter import chapter_bp
from routes.reader import reader_bp
from routes.notifications import notifications_bp
from routes.continue_reading import continue_bp

app.register_blueprint(continue_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(story_bp)
app.register_blueprint(chapter_bp)
app.register_blueprint(reader_bp)
app.register_blueprint(notifications_bp)

# =========================================================
# HTML ROUTES
# =========================================================

# ---------- COMMON ----------
@app.route("/")
@app.route("/login")
def login():
    return send_from_directory(ROOT_PATH, "LOGIN.html")


@app.route("/register")
def register():
    return send_from_directory(ROOT_PATH, "REGISTER.html")


# ---------- WRITER ----------
@app.route("/writer-dashboard")
def writer_dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(ROOT_PATH, "WRITER_DASHBOARD.html")


@app.route("/add-chapter")
def add_chapter():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(ROOT_PATH, "ADD_CHAPTER.html")


@app.route("/story-details-writer")
def story_details_writer():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(ROOT_PATH, "STORY_DETAILS.html")


@app.route("/create-story")
def create_story_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(ROOT_PATH, "CREATE_STORY.html")


@app.route("/writer-profile")
def writer_profile():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(ROOT_PATH, "WRITER_PROFILE.html")


# ---------- READER ----------
@app.route("/reader-register")
def reader_register():
    return send_from_directory(READERS_PATH, "reader_registration.html")


@app.route("/reader-dashboard")
def reader_dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "reader_dashboard.html")


@app.route("/reader-reading")
def reader_reading():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "reader_reading.html")


@app.route("/story-details")
def story_details():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "reader_story_details.html")


@app.route("/library")
def library():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "library.html")


@app.route("/search")
def search():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "search.html")


@app.route("/notifications")
def notifications():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "notifications.html")


@app.route("/reader-profile")
def reader_profile():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory(READERS_PATH, "PROFILE.html")


# =========================================================
# SERVE UPLOAD FILES
# =========================================================

@app.route("/uploads/<path:filepath>")
def serve_upload(filepath):
    return send_from_directory(UPLOAD_ROOT, filepath)


# =========================================================
# 🔥 NEW FIX: DIRECT HTML ACCESS SUPPORT
# =========================================================

@app.route('/<path:filename>')
def serve_html(filename):
    # root html
    root_file = os.path.join(ROOT_PATH, filename)
    if os.path.exists(root_file):
        return send_from_directory(ROOT_PATH, filename)

    # reader html
    reader_file = os.path.join(READERS_PATH, filename)
    if os.path.exists(reader_file):
        return send_from_directory(READERS_PATH, filename)

    return {"error": "Route not found"}, 404


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):
    return {"error": "Route not found"}, 404


@app.errorhandler(500)
def server_error(error):
    return {"error": "Internal server error"}, 500


# =========================================================
# TEST
# =========================================================

@app.route("/test")
def test():
    return "APP IS WORKING"


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)