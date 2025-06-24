from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
import bcrypt
from config.db import connect_db

# Connect to MongoDB
db = connect_db()
users = db['users']

# Define auth blueprint
auth_bp = Blueprint('auth', __name__)

# -----------------------------
# SIGNUP ROUTE
# -----------------------------
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    # Validate required fields
    if not username or not email or not password or not role:
        return jsonify({"error": "All fields (username, email, password, role) are required"}), 400

    # Check if user already exists with same username or email
    if users.find_one({'$or': [{'username': username}, {'email': email}]}):
        return jsonify({"error": "Username or Email already exists"}), 409

    # Hash password using bcrypt
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create new user document
    user_doc = {
        'username': username,
        'email': email,
        'password': hashed_pw,
        'role': role
    }

    # Insert user into MongoDB
    result = users.insert_one(user_doc)

    return jsonify({"message": "User registered successfully", "user_id": str(result.inserted_id)}), 201


# -----------------------------
# LOGIN ROUTE
# -----------------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('username') or data.get('email')  # Login via username or email
    password = data.get('password')

    if not identifier or not password:
        return jsonify({"error": "Username/Email and password are required"}), 400

    # Search by either email or username
    user = users.find_one({
        '$or': [{'username': identifier}, {'email': identifier}]
    })

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check password using bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    # Return user data (omit password)
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "role": user['role']
        }
    }), 200
