from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from config.db import connect_db

db = connect_db()

admin_bp = Blueprint("admin", __name__)
users_col    = db["users"]
projects_col = db["projects"]
access_col   = db["access_requests"]   # if you store pending requests separately

# ---------- GET /access_requests ----------
@admin_bp.route("/access_requests", methods=["GET"])
def access_requests():
    # optional filter by admin GitHub username
    # github_username = request.args.get("adminGithubUsername")
    requests = list(access_col.find({}, {"_id": 0}))
    return jsonify({"requests": requests}), 200

# ---------- POST /create_project ----------
@admin_bp.route("/create_project", methods=["POST"])
def create_project():
    data = request.get_json()
    name        = data.get("name")
    description = data.get("description")
    admin_gh    = data.get("adminGithubUsername")

    if not all([name, description, admin_gh]):
        return jsonify({"error": "Missing required fields"}), 400

    doc = {
        "projectName":          name,
        "description":          description,
        "adminGithubUsername":  admin_gh,
        "assignedUsers":        [],
        "createdAt":            data.get("createdAt")
    }
    res = projects_col.insert_one(doc)
    return jsonify({"message": "Project created", "id": str(res.inserted_id)}), 201

# ---------- GET /commits/<github_username> ----------
@admin_bp.route("/commits/<github_username>", methods=["GET"])
def admin_projects(github_username):
    projects = list(projects_col.find({"adminGithubUsername": github_username}))
    for p in projects:
        p["_id"] = str(p["_id"])
    return jsonify({"projects": projects}), 200

# ---------- POST /assign_user_to_project ----------
@admin_bp.route("/assign_user_to_project", methods=["POST"])
def assign_user():
    data       = request.get_json()
    project_id = data.get("projectId")
    user_id    = data.get("userId")
    role       = data.get("role")

    if role not in ("developer", "auditor"):
        return jsonify({"error": "Invalid role"}), 400

    if not all([project_id, user_id, role]):
        return jsonify({"error": "Missing data"}), 400

    # verify project exists
    project = projects_col.find_one({"_id": ObjectId(project_id)})
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # verify user exists
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # check duplicate assignment
    if any(u["userId"] == user_id for u in project.get("assignedUsers", [])):
        return jsonify({"error": "User already assigned"}), 409

    projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {"$push": {"assignedUsers": {"userId": user_id, "role": role}}}
    )
    return jsonify({"message": "User assigned"}), 200
