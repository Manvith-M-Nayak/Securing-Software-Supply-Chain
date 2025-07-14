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
    user_data = {
        "id":               str(doc["_id"]),
        "username":         doc["username"],
        "email":            doc["email"],
        "role":             doc["role"],
        "githubUsername":   doc.get("githubUsername", "")
    }
    
    # Add role-specific project fields
    if doc["role"] == "admin":
        user_data["createdProjects"] = doc.get("createdProjects", [])
    else:
        user_data["assignedProjects"] = doc.get("assignedProjects", [])
    
    return user_data

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
    assigned_projects = data.get("assignedProjects", [])  # For developers/auditors
    created_projects = data.get("createdProjects", [])    # For admins

    # 1) basic validation
    if not all([username, email, password, role, github_username]):
        return jsonify({"error": "username, email, password, role, and githubUsername are all required"}), 400

    # 2) ensure uniqueness
    if users_col.find_one({"$or": [{"username": username}, {"email": email}]}):
        return jsonify({"error": "Username or email already exists"}), 409

    # 3) hash password
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # 4) build user document based on role
    user_doc = {
        "username":         username,
        "email":            email,
        "password":         hashed_pw,
        "role":             role,
        "githubUsername":   github_username
    }
    
    # Add role-specific project fields
    if role == "admin":
        user_doc["createdProjects"] = created_projects
    else:
        user_doc["assignedProjects"] = assigned_projects

    # 5) insert document
    res = users_col.insert_one(user_doc)
    user_doc["_id"] = res.inserted_id

    # 6) return created user
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

# --------------------------------------------------
#  PUT /api/auth/users/<user_id>/assign-projects
# --------------------------------------------------
@auth_bp.route("/users/<user_id>/assign-projects", methods=["PUT"])
def assign_projects(user_id):
    """Assign projects to a user (developers/auditors only)"""
    data = request.get_json() or {}
    projects = data.get("projects", [])
    
    if not isinstance(projects, list):
        return jsonify({"error": "Projects must be an array"}), 400
    
    try:
        # First check if user exists and get their role
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        if user_doc["role"] == "admin":
            return jsonify({"error": "Cannot assign projects to admin users. Use create-projects endpoint instead."}), 400
        
        # Update user's assigned projects
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"assignedProjects": projects}}
        )
        
        # Return updated user
        updated_user = users_col.find_one({"_id": ObjectId(user_id)})
        return jsonify({"user": serialize_user(updated_user)}), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400

# --------------------------------------------------
#  PUT /api/auth/users/<user_id>/create-projects
# --------------------------------------------------
@auth_bp.route("/users/<user_id>/create-projects", methods=["PUT"])
def create_projects(user_id):
    """Set created projects for admin users"""
    data = request.get_json() or {}
    projects = data.get("projects", [])
    
    if not isinstance(projects, list):
        return jsonify({"error": "Projects must be an array"}), 400
    
    try:
        # First check if user exists and get their role
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        if user_doc["role"] != "admin":
            return jsonify({"error": "Only admin users can have created projects"}), 400
        
        # Update user's created projects
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"createdProjects": projects}}
        )
        
        # Return updated user
        updated_user = users_col.find_one({"_id": ObjectId(user_id)})
        return jsonify({"user": serialize_user(updated_user)}), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400

# --------------------------------------------------
#  POST /api/auth/users/<user_id>/add-project
# --------------------------------------------------
@auth_bp.route("/users/<user_id>/add-project", methods=["POST"])
def add_project_to_user(user_id):
    """Add a single project to user's projects"""
    data = request.get_json() or {}
    project = data.get("project")
    
    if not project:
        return jsonify({"error": "Project is required"}), 400
    
    try:
        # First check if user exists and get their role
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Add project to appropriate field based on role
        if user_doc["role"] == "admin":
            field = "createdProjects"
        else:
            field = "assignedProjects"
        
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {field: project}}
        )
        
        # Return updated user
        updated_user = users_col.find_one({"_id": ObjectId(user_id)})
        return jsonify({"user": serialize_user(updated_user)}), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400

# --------------------------------------------------
#  DELETE /api/auth/users/<user_id>/remove-project
# --------------------------------------------------
@auth_bp.route("/users/<user_id>/remove-project", methods=["DELETE"])
def remove_project_from_user(user_id):
    """Remove a project from user's projects"""
    data = request.get_json() or {}
    project = data.get("project")
    
    if not project:
        return jsonify({"error": "Project is required"}), 400
    
    try:
        # First check if user exists and get their role
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Remove project from appropriate field based on role
        if user_doc["role"] == "admin":
            field = "createdProjects"
        else:
            field = "assignedProjects"
        
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {field: project}}
        )
        
        # Return updated user
        updated_user = users_col.find_one({"_id": ObjectId(user_id)})
        return jsonify({"user": serialize_user(updated_user)}), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400

# --------------------------------------------------
#  GET /api/auth/users/<user_id>/projects
# --------------------------------------------------
@auth_bp.route("/users/<user_id>/projects", methods=["GET"])
def get_user_projects(user_id):
    """Get user's projects"""
    try:
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        response_data = {
            "userId": user_id,
            "username": user_doc["username"],
            "role": user_doc["role"]
        }
        
        # Add role-specific project data
        if user_doc["role"] == "admin":
            response_data["createdProjects"] = user_doc.get("createdProjects", [])
        else:
            response_data["assignedProjects"] = user_doc.get("assignedProjects", [])
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400

# --------------------------------------------------
#  GET /api/auth/users
# --------------------------------------------------
@auth_bp.route("/users", methods=["GET"])
def get_all_users():
    """Get all users (for admin purposes)"""
    try:
        users = users_col.find({}, {"password": 0})  # Exclude password field
        user_list = [serialize_user(user) for user in users]
        return jsonify({"users": user_list}), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch users"}), 500

# --------------------------------------------------
#  GET /api/auth/users/<user_id>
# --------------------------------------------------
@auth_bp.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """Get a specific user by ID"""
    try:
        user_doc = users_col.find_one({"_id": ObjectId(user_id)})
        
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"user": serialize_user(user_doc)}), 200
        
    except Exception as e:
        return jsonify({"error": "Invalid user ID"}), 400