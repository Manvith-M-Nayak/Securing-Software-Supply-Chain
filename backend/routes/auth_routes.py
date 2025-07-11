from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
import bcrypt
from config.db import connect_db

# --------------------------------------------------
# Mongo connection & Blueprint
# --------------------------------------------------
db = connect_db()
users_col = db["users"]

auth_bp = Blueprint("auth", __name__)

# --------------------------------------------------
# Helper: serialize user (omit password hash)
# --------------------------------------------------
def serialize_user(doc):
    return {
        "id":            str(doc["_id"]),
        "username":      doc["username"],
        "email":         doc["email"],
        "role":          doc["role"],
        "githubUsername": doc.get("githubUsername", "")
    }

# --------------------------------------------------
#  POST /api/auth/signup
# --------------------------------------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}

    username        = data.get("username", "").strip()
    email           = data.get("email", "").strip().lower()
    password        = data.get("password", "")
    role            = data.get("role", "").strip().lower()
    github_username = data.get("githubUsername", "").strip()

    # 1) basic validation
    if not all([username, email, password, role, github_username]):
        return jsonify({"error": "username, email, password, role, and githubUsername are all required"}), 400

    # 2) ensure uniqueness
    if users_col.find_one({"$or": [{"username": username}, {"email": email}]}):
        return jsonify({"error": "Username or email already exists"}), 409

    # 3) hash password
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # 4) insert document
    user_doc = {
        "username":       username,
        "email":          email,
        "password":       hashed_pw,
        "role":           role,
        "githubUsername": github_username
    }
    res = users_col.insert_one(user_doc)
    user_doc["_id"] = res.inserted_id

    # 5) return created user
    return jsonify({"user": serialize_user(user_doc)}), 201

# --------------------------------------------------
#  POST /api/auth/login
# --------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    identifier = data.get("username") or data.get("email")
    password   = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Username/Email and password are required"}), 400

    # 1) find user by username or email
    user_doc = users_col.find_one({
        "$or": [
            {"username": identifier.strip()},
            {"email": identifier.strip().lower()}
        ]
    })
    if not user_doc:
        return jsonify({"error": "User not found"}), 404

    # 2) verify password
    if not bcrypt.checkpw(password.encode("utf-8"), user_doc["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # 3) success
    return jsonify({"user": serialize_user(user_doc)}), 200
