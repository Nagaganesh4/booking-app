import os
import certifi
import cloudinary
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from pymongo import MongoClient
from config import (
    MONGO_URI, SECRET_KEY,
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
)

# ── Cloudinary setup ───────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# ── Flask app factory ──────────────────────────────────────────────────────────
def create_app():
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config["SECRET_KEY"] = SECRET_KEY
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── MongoDB (lazy — inside factory so Vercel doesn't timeout on import) ───
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(),
                         serverSelectionTimeoutMS=5000,
                         connectTimeoutMS=5000,
                         socketTimeoutMS=10000)
    db = client.get_default_database()
    if db.name in ("admin", None):
        db = client["moviebooking"]

    # TTL index for seat locks
    try:
        db.seat_locks.create_index("expires_at", expireAfterSeconds=0)
    except Exception:
        pass

    app.db = db

    # Register blueprints
    from routes.auth import auth_bp
    from routes.movies import movies_bp
    from routes.theaters import theaters_bp
    from routes.bookings import bookings_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(movies_bp,   url_prefix="/api/movies")
    app.register_blueprint(theaters_bp, url_prefix="/api")
    app.register_blueprint(bookings_bp, url_prefix="/api")
    app.register_blueprint(admin_bp,    url_prefix="/api/admin")

    # ── Serve frontend static files for all non-API routes ───────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        target = os.path.join(frontend_dir, path)
        if path and os.path.exists(target):
            return send_from_directory(frontend_dir, path)
        return send_file(os.path.join(frontend_dir, "index.html"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
