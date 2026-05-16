from flask import Blueprint, request, jsonify, current_app
from utils.auth_middleware import hash_password, check_password, generate_token, token_required
from bson import ObjectId

auth_bp = Blueprint("auth", __name__)


def get_db():
    return current_app.db


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    db = get_db()

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([name, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    user = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "role": "user",
    }
    result = db.users.insert_one(user)
    token = generate_token(str(result.inserted_id), "user")
    return jsonify({
        "message": "Registration successful",
        "token": token,
        "user": {"id": str(result.inserted_id), "name": name, "email": email, "role": "user"}
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    db = get_db()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = db.users.find_one({"email": email})
    if not user or not check_password(password, user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(str(user["_id"]), user.get("role", "user"))
    return jsonify({
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user")
        }
    })


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(request.user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "user")
    })
