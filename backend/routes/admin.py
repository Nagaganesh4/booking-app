from flask import Blueprint, request, jsonify, current_app
from utils.auth_middleware import admin_required
from bson import ObjectId

admin_bp = Blueprint("admin", __name__)


def get_db():
    return current_app.db


@admin_bp.route("/analytics", methods=["GET"])
@admin_required
def analytics():
    db = get_db()

    total_bookings = db.bookings.count_documents({"status": "confirmed"})
    cancelled = db.bookings.count_documents({"status": "cancelled"})
    total_movies = db.movies.count_documents({"is_active": True})
    total_theaters = db.theaters.count_documents({})
    total_shows = db.shows.count_documents({})

    # Revenue
    pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]
    rev_result = list(db.bookings.aggregate(pipeline))
    total_revenue = rev_result[0]["total"] if rev_result else 0

    # Top movies by bookings
    top_movies_pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": "$movie_title", "count": {"$sum": 1}, "revenue": {"$sum": "$total_price"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_movies = [
        {"movie": d["_id"], "bookings": d["count"], "revenue": d["revenue"]}
        for d in db.bookings.aggregate(top_movies_pipeline)
    ]

    # Recent bookings
    recent = list(db.bookings.find().sort("booked_at", -1).limit(10))
    recent_list = []
    for b in recent:
        recent_list.append({
            "id": str(b["_id"]),
            "user_name": b.get("user_name", ""),
            "user_email": b.get("user_email", ""),
            "movie_title": b.get("movie_title", ""),
            "theater_name": b.get("theater_name", ""),
            "seats": b.get("seats", []),
            "total_price": b.get("total_price", 0),
            "status": b.get("status", ""),
            "booked_at": b.get("booked_at", ""),
        })

    return jsonify({
        "total_bookings": total_bookings,
        "cancelled_bookings": cancelled,
        "total_movies": total_movies,
        "total_theaters": total_theaters,
        "total_shows": total_shows,
        "total_revenue": total_revenue,
        "top_movies": top_movies,
        "recent_bookings": recent_list,
    })


@admin_bp.route("/bookings", methods=["GET"])
@admin_required
def all_bookings():
    db = get_db()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    status = request.args.get("status")

    query = {}
    if status:
        query["status"] = status

    total = db.bookings.count_documents(query)
    bookings = list(
        db.bookings.find(query)
        .sort("booked_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    result = []
    for b in bookings:
        result.append({
            "id": str(b["_id"]),
            "user_name": b.get("user_name", ""),
            "user_email": b.get("user_email", ""),
            "movie_title": b.get("movie_title", ""),
            "theater_name": b.get("theater_name", ""),
            "theater_city": b.get("theater_city", ""),
            "show_datetime": b.get("show_datetime", ""),
            "screen_no": b.get("screen_no", 1),
            "seats": b.get("seats", []),
            "total_price": b.get("total_price", 0),
            "status": b.get("status", ""),
            "booked_at": b.get("booked_at", ""),
        })

    return jsonify({"total": total, "page": page, "per_page": per_page, "bookings": result})
