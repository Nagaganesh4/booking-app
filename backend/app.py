from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
import certifi
import cloudinary
from config import (
    MONGO_URI, SECRET_KEY,
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
)

# ── Cloudinary setup ──────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# ── MongoDB ───────────────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client.get_default_database() if "mongodb+srv" in MONGO_URI or "/" in MONGO_URI.split("@")[-1] else client["moviebooking"]

# Ensure the db name is consistent when using Atlas URIs without explicit db name
if db.name == "admin" or db.name is None:
    db = client["moviebooking"]

# TTL index for seat locks (auto-expire after 10 minutes)
try:
    db.seat_locks.create_index("expires_at", expireAfterSeconds=0)
except Exception:
    pass

# ── Flask app ─────────────────────────────────────────────────────────────────
def create_app():
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config["SECRET_KEY"] = SECRET_KEY
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Attach db to app context
    app.db = db

    # Register blueprints
    from routes.auth import auth_bp
    from routes.movies import movies_bp
    from routes.theaters import theaters_bp
    from routes.bookings import bookings_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(movies_bp, url_prefix="/api/movies")
    app.register_blueprint(theaters_bp, url_prefix="/api")
    app.register_blueprint(bookings_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # Serve frontend index.html for all non-API routes
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        import os
        from flask import send_from_directory, send_file
        frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend")
        target = os.path.join(frontend_dir, path)
        if path and os.path.exists(target):
            return send_from_directory(frontend_dir, path)
        return send_file(os.path.join(frontend_dir, "index.html"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
