from flask import Blueprint, request, jsonify, current_app
from utils.auth_middleware import token_required
from bson import ObjectId
from datetime import datetime, timezone, timedelta

bookings_bp = Blueprint("bookings", __name__)


def get_db():
    return current_app.db


def build_seat_grid(rows, cols):
    """Generate seat IDs like A1, A2 ... H10."""
    row_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    seats = []
    for r in range(rows):
        for c in range(1, cols + 1):
            seats.append(f"{row_labels[r]}{c}")
    return seats


def serialize_booking(b):
    return {
        "id": str(b["_id"]),
        "show_id": str(b.get("show_id", "")),
        "user_id": str(b.get("user_id", "")),
        "user_name": b.get("user_name", ""),
        "user_email": b.get("user_email", ""),
        "movie_title": b.get("movie_title", ""),
        "theater_name": b.get("theater_name", ""),
        "theater_city": b.get("theater_city", ""),
        "show_datetime": b.get("show_datetime", ""),
        "screen_no": b.get("screen_no", 1),
        "seats": b.get("seats", []),
        "total_price": b.get("total_price", 0),
        "status": b.get("status", "confirmed"),
        "booked_at": b.get("booked_at", ""),
    }


@bookings_bp.route("/shows/<show_id>/seats", methods=["GET"])
def get_seat_map(show_id):
    """Return all seats with available/booked status."""
    db = get_db()
    try:
        oid = ObjectId(show_id)
    except Exception:
        return jsonify({"error": "Invalid show ID"}), 400

    show = db.shows.find_one({"_id": oid})
    if not show:
        return jsonify({"error": "Show not found"}), 404

    all_seats = build_seat_grid(show.get("rows", 8), show.get("cols", 10))

    # Collect booked seats from confirmed bookings
    booked_seats = set()
    for booking in db.bookings.find({"show_id": oid, "status": "confirmed"}):
        booked_seats.update(booking.get("seats", []))

    # Collect temporarily locked seats (still valid TTL)
    locked_seats = set()
    now = datetime.now(timezone.utc)
    for lock in db.seat_locks.find({"show_id": oid, "expires_at": {"$gt": now}}):
        locked_seats.add(lock.get("seat"))

    seat_map = []
    for seat in all_seats:
        if seat in booked_seats:
            status = "booked"
        elif seat in locked_seats:
            status = "locked"
        else:
            status = "available"
        seat_map.append({"seat": seat, "status": status})

    return jsonify({
        "show_id": show_id,
        "movie_title": show.get("movie_title", ""),
        "theater_name": show.get("theater_name", ""),
        "theater_city": show.get("theater_city", ""),
        "datetime": show.get("datetime", ""),
        "screen_no": show.get("screen_no", 1),
        "price": show.get("price", 150),
        "rows": show.get("rows", 8),
        "cols": show.get("cols", 10),
        "seats": seat_map,
    })


@bookings_bp.route("/bookings", methods=["POST"])
@token_required
def create_booking():
    db = get_db()
    data = request.get_json() or {}

    show_id_str = data.get("show_id", "")
    selected_seats = data.get("seats", [])

    if not show_id_str or not selected_seats:
        return jsonify({"error": "show_id and seats are required"}), 400

    try:
        show_oid = ObjectId(show_id_str)
    except Exception:
        return jsonify({"error": "Invalid show ID"}), 400

    show = db.shows.find_one({"_id": show_oid})
    if not show:
        return jsonify({"error": "Show not found"}), 404

    # Validate seats not already booked
    booked_seats = set()
    for booking in db.bookings.find({"show_id": show_oid, "status": "confirmed"}):
        booked_seats.update(booking.get("seats", []))

    conflicts = [s for s in selected_seats if s in booked_seats]
    if conflicts:
        return jsonify({"error": f"Seats already booked: {', '.join(conflicts)}"}), 409

    # Get user info
    user = db.users.find_one({"_id": ObjectId(request.user_id)})

    total_price = len(selected_seats) * show.get("price", 150)

    booking = {
        "show_id": show_oid,
        "user_id": ObjectId(request.user_id),
        "user_name": user.get("name", "") if user else "",
        "user_email": user.get("email", "") if user else "",
        "movie_title": show.get("movie_title", ""),
        "movie_poster": show.get("movie_poster", ""),
        "theater_name": show.get("theater_name", ""),
        "theater_city": show.get("theater_city", ""),
        "show_datetime": show.get("datetime", ""),
        "screen_no": show.get("screen_no", 1),
        "seats": selected_seats,
        "total_price": total_price,
        "status": "confirmed",
        "booked_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.bookings.insert_one(booking)

    # Remove any seat locks for these seats
    db.seat_locks.delete_many({"show_id": show_oid, "seat": {"$in": selected_seats}})

    return jsonify({
        "message": "Booking confirmed!",
        "booking_id": str(result.inserted_id),
        "seats": selected_seats,
        "total_price": total_price,
        "movie_title": show.get("movie_title", ""),
        "theater_name": show.get("theater_name", ""),
        "show_datetime": show.get("datetime", ""),
    }), 201


@bookings_bp.route("/bookings/me", methods=["GET"])
@token_required
def my_bookings():
    db = get_db()
    bookings = list(db.bookings.find(
        {"user_id": ObjectId(request.user_id)},
    ).sort("booked_at", -1))
    return jsonify([serialize_booking(b) for b in bookings])


@bookings_bp.route("/bookings/<booking_id>/cancel", methods=["PUT"])
@token_required
def cancel_booking(booking_id):
    db = get_db()
    try:
        oid = ObjectId(booking_id)
    except Exception:
        return jsonify({"error": "Invalid booking ID"}), 400

    booking = db.bookings.find_one({"_id": oid, "user_id": ObjectId(request.user_id)})
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if booking.get("status") == "cancelled":
        return jsonify({"error": "Already cancelled"}), 400

    db.bookings.update_one({"_id": oid}, {"$set": {"status": "cancelled"}})
    return jsonify({"message": "Booking cancelled"})
