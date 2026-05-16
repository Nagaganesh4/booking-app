from flask import Blueprint, request, jsonify, current_app
from utils.auth_middleware import admin_required
from bson import ObjectId
import cloudinary.uploader

movies_bp = Blueprint("movies", __name__)


def get_db():
    return current_app.db


def serialize_movie(m):
    return {
        "id": str(m["_id"]),
        "title": m.get("title", ""),
        "genre": m.get("genre", ""),
        "language": m.get("language", ""),
        "duration": m.get("duration", ""),
        "description": m.get("description", ""),
        "rating": m.get("rating", 0),
        "poster_url": m.get("poster_url", ""),
        "cast": m.get("cast", []),
        "is_active": m.get("is_active", True),
    }


@movies_bp.route("/", methods=["GET"])
def list_movies():
    db = get_db()
    query = {"is_active": True}
    genre = request.args.get("genre")
    search = request.args.get("search")
    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    movies = list(db.movies.find(query).sort("_id", -1))
    return jsonify([serialize_movie(m) for m in movies])


@movies_bp.route("/<movie_id>", methods=["GET"])
def get_movie(movie_id):
    db = get_db()
    try:
        movie = db.movies.find_one({"_id": ObjectId(movie_id)})
    except Exception:
        return jsonify({"error": "Invalid movie ID"}), 400
    if not movie:
        return jsonify({"error": "Movie not found"}), 404
    return jsonify(serialize_movie(movie))


@movies_bp.route("/", methods=["POST"])
@admin_required
def add_movie():
    db = get_db()
    poster_url = ""

    # Handle multipart (with image file) or JSON (with url)
    if request.content_type and "multipart" in request.content_type:
        data = request.form
        file = request.files.get("poster")
        if file:
            result = cloudinary.uploader.upload(file, folder="moviebooking/posters")
            poster_url = result.get("secure_url", "")
    else:
        data = request.get_json() or {}
        poster_url = data.get("poster_url", "")

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Movie title is required"}), 400

    movie = {
        "title": title,
        "genre": data.get("genre", ""),
        "language": data.get("language", "Hindi"),
        "duration": data.get("duration", ""),
        "description": data.get("description", ""),
        "rating": float(data.get("rating", 0)),
        "cast": data.get("cast", []),
        "poster_url": poster_url,
        "is_active": True,
    }
    result = db.movies.insert_one(movie)
    movie["id"] = str(result.inserted_id)
    movie.pop("_id", None)
    return jsonify(movie), 201


@movies_bp.route("/<movie_id>", methods=["PUT"])
@admin_required
def update_movie(movie_id):
    db = get_db()
    try:
        oid = ObjectId(movie_id)
    except Exception:
        return jsonify({"error": "Invalid movie ID"}), 400

    poster_url = None
    if request.content_type and "multipart" in request.content_type:
        data = request.form
        file = request.files.get("poster")
        if file:
            result = cloudinary.uploader.upload(file, folder="moviebooking/posters")
            poster_url = result.get("secure_url", "")
    else:
        data = request.get_json() or {}
        poster_url = data.get("poster_url")

    update = {}
    for field in ["title", "genre", "language", "duration", "description", "cast"]:
        if field in data:
            update[field] = data[field]
    if "rating" in data:
        update["rating"] = float(data["rating"])
    if "is_active" in data:
        update["is_active"] = bool(data["is_active"])
    if poster_url is not None:
        update["poster_url"] = poster_url

    db.movies.update_one({"_id": oid}, {"$set": update})
    movie = db.movies.find_one({"_id": oid})
    return jsonify(serialize_movie(movie))


@movies_bp.route("/<movie_id>", methods=["DELETE"])
@admin_required
def delete_movie(movie_id):
    db = get_db()
    try:
        oid = ObjectId(movie_id)
    except Exception:
        return jsonify({"error": "Invalid movie ID"}), 400
    # Soft delete
    db.movies.update_one({"_id": oid}, {"$set": {"is_active": False}})
    return jsonify({"message": "Movie removed successfully"})
