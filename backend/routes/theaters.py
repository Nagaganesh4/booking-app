from flask import Blueprint, request, jsonify, current_app
from utils.auth_middleware import admin_required
from bson import ObjectId
from datetime import datetime

theaters_bp = Blueprint("theaters", __name__)


def get_db():
    return current_app.db


def serialize_theater(t):
    return {
        "id": str(t["_id"]),
        "name": t.get("name", ""),
        "location": t.get("location", ""),
        "city": t.get("city", ""),
        "screens": t.get("screens", []),
    }


def serialize_show(s):
    return {
        "id": str(s["_id"]),
        "movie_id": str(s.get("movie_id", "")),
        "theater_id": str(s.get("theater_id", "")),
        "movie_title": s.get("movie_title", ""),
        "movie_poster": s.get("movie_poster", ""),
        "theater_name": s.get("theater_name", ""),
        "theater_city": s.get("theater_city", ""),
        "screen_no": s.get("screen_no", 1),
        "datetime": s.get("datetime", ""),
        "price": s.get("price", 150),
        "rows": s.get("rows", 8),
        "cols": s.get("cols", 10),
    }


# ── Theaters ──────────────────────────────────────────────────────────────────

@theaters_bp.route("/theaters", methods=["GET"])
def list_theaters():
    db = get_db()
    theaters = list(db.theaters.find())
    return jsonify([serialize_theater(t) for t in theaters])


@theaters_bp.route("/theaters/<theater_id>", methods=["GET"])
def get_theater(theater_id):
    db = get_db()
    try:
        t = db.theaters.find_one({"_id": ObjectId(theater_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not t:
        return jsonify({"error": "Theater not found"}), 404
    return jsonify(serialize_theater(t))


@theaters_bp.route("/theaters", methods=["POST"])
@admin_required
def add_theater():
    db = get_db()
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Theater name is required"}), 400

    # Default screens: build from screen count
    screen_count = int(data.get("screen_count", 1))
    screens = []
    for i in range(1, screen_count + 1):
        screens.append({"screen_no": i, "rows": data.get("rows", 8), "cols": data.get("cols", 10)})

    theater = {
        "name": name,
        "location": data.get("location", ""),
        "city": data.get("city", ""),
        "screens": screens,
    }
    result = db.theaters.insert_one(theater)
    theater["id"] = str(result.inserted_id)
    theater.pop("_id", None)
    return jsonify(theater), 201


@theaters_bp.route("/theaters/<theater_id>", methods=["PUT"])
@admin_required
def update_theater(theater_id):
    db = get_db()
    try:
        oid = ObjectId(theater_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    data = request.get_json() or {}
    update = {}
    for field in ["name", "location", "city", "screens"]:
        if field in data:
            update[field] = data[field]
    db.theaters.update_one({"_id": oid}, {"$set": update})
    t = db.theaters.find_one({"_id": oid})
    return jsonify(serialize_theater(t))


@theaters_bp.route("/theaters/<theater_id>", methods=["DELETE"])
@admin_required
def delete_theater(theater_id):
    db = get_db()
    try:
        oid = ObjectId(theater_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    db.theaters.delete_one({"_id": oid})
    return jsonify({"message": "Theater deleted"})


# ── Shows ─────────────────────────────────────────────────────────────────────

@theaters_bp.route("/shows", methods=["GET"])
def list_shows():
    db = get_db()
    query = {}
    movie_id = request.args.get("movie_id")
    theater_id = request.args.get("theater_id")
    date = request.args.get("date")   # YYYY-MM-DD

    if movie_id:
        try:
            query["movie_id"] = ObjectId(movie_id)
        except Exception:
            pass
    if theater_id:
        try:
            query["theater_id"] = ObjectId(theater_id)
        except Exception:
            pass
    if date:
        query["datetime"] = {"$regex": f"^{date}"}

    shows = list(db.shows.find(query).sort("datetime", 1))
    return jsonify([serialize_show(s) for s in shows])


@theaters_bp.route("/shows/<show_id>", methods=["GET"])
def get_show(show_id):
    db = get_db()
    try:
        s = db.shows.find_one({"_id": ObjectId(show_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not s:
        return jsonify({"error": "Show not found"}), 404
    return jsonify(serialize_show(s))


@theaters_bp.route("/shows", methods=["POST"])
@admin_required
def add_show():
    db = get_db()
    data = request.get_json() or {}

    try:
        movie_id = ObjectId(data["movie_id"])
        theater_id = ObjectId(data["theater_id"])
    except Exception:
        return jsonify({"error": "Invalid movie or theater ID"}), 400

    movie = db.movies.find_one({"_id": movie_id})
    theater = db.theaters.find_one({"_id": theater_id})
    if not movie or not theater:
        return jsonify({"error": "Movie or theater not found"}), 404

    screen_no = int(data.get("screen_no", 1))
    # Find screen config
    screen = next((s for s in theater.get("screens", []) if s["screen_no"] == screen_no), None)
    rows = screen["rows"] if screen else data.get("rows", 8)
    cols = screen["cols"] if screen else data.get("cols", 10)

    show = {
        "movie_id": movie_id,
        "theater_id": theater_id,
        "movie_title": movie.get("title", ""),
        "movie_poster": movie.get("poster_url", ""),
        "theater_name": theater.get("name", ""),
        "theater_city": theater.get("city", ""),
        "screen_no": screen_no,
        "datetime": data.get("datetime", ""),
        "price": float(data.get("price", 150)),
        "rows": int(rows),
        "cols": int(cols),
    }
    result = db.shows.insert_one(show)
    show["id"] = str(result.inserted_id)
    show["movie_id"] = str(movie_id)
    show["theater_id"] = str(theater_id)
    show.pop("_id", None)
    return jsonify(show), 201


@theaters_bp.route("/shows/<show_id>", methods=["DELETE"])
@admin_required
def delete_show(show_id):
    db = get_db()
    try:
        oid = ObjectId(show_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    db.shows.delete_one({"_id": oid})
    return jsonify({"message": "Show deleted"})
