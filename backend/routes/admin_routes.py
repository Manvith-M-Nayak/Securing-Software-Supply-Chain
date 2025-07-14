from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from config.db import connect_db

db = connect_db()

admin_bp = Blueprint("admin", __name__)
users_col    = db["users"]
projects_col = db["projects"]
access_col   = db["access_requests"]   # if you store pending requests separately

# ---------- GET /users ----------
@admin_bp.route("/users", methods=["GET"])
def get_users():
    """Get all users with developer or auditor roles"""
    try:
        # Get all users with developer or auditor roles
        users = list(users_col.find(
            {"role": {"$in": ["developer", "auditor"]}},
            {"password": 0}  # Exclude password field for security
        ))
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            user["_id"] = str(user["_id"])
        
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
# ---------- GET /available_users ----------
@admin_bp.route("/available_users", methods=["GET"])
def get_available_users():
    """Get all available developers and auditors that can be assigned to projects"""
    try:
        # Get all users with developer or auditor roles
        users = list(users_col.find(
            {"role": {"$in": ["developer", "auditor"]}},
            {"_id": 1, "username": 1, "githubUsername": 1, "role": 1, "email": 1}
        ))
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            user["_id"] = str(user["_id"])
        
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- POST /create_project ----------
@admin_bp.route("/create_project", methods=["POST"])
def create_project():
    data = request.get_json()
    name        = data.get("name")
    admin_gh    = data.get("adminGithubUsername")

    if not all([name, admin_gh]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Update the admin user's createdProjects array with the project name
        result = users_col.update_one(
            {"githubUsername": admin_gh},
            {"$push": {"createdProjects": name}}
        )
        
        # Check if the admin user was found and updated
        if result.matched_count == 0:
            return jsonify({"error": "Admin user not found"}), 404
        
        return jsonify({"message": "Project created successfully"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- GET /commits/<github_username> ----------
@admin_bp.route("/commits/<github_username>", methods=["GET"])
def admin_projects(github_username):
    """Get all projects created by the admin user from their createdProjects array"""
    try:
        # Find the admin user and get their created projects
        admin_user = users_col.find_one({"githubUsername": github_username})
        if not admin_user:
            return jsonify({"error": "Admin user not found"}), 404
        
        created_projects = admin_user.get("createdProjects", [])
        
        # Create project objects with assigned users info
        projects = []
        for project_name in created_projects:
            # Find all users who have this project in their assignedProjects
            assigned_users = []
            users_with_project = users_col.find({
                "assignedProjects.projectName": project_name
            })
            
            for user in users_with_project:
                user_projects = user.get("assignedProjects", [])
                for project_assignment in user_projects:
                    if project_assignment.get("projectName") == project_name:
                        assigned_users.append({
                            "userId": str(user["_id"]),
                            "username": user.get("username"),
                            "githubUsername": user.get("githubUsername"),
                            "role": project_assignment.get("role"),
                            "assignedAt": project_assignment.get("assignedAt")
                        })
                        break
            
            # Create project object
            project = {
                "_id": project_name,  # Use project name as ID since there's no separate projects collection
                "name": project_name,
                "assignedUsers": assigned_users,
                "adminGithubUsername": github_username
            }
            projects.append(project)
        
        return jsonify({"projects": projects}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- POST /assign_user_to_project ----------
@admin_bp.route("/assign_user_to_project", methods=["POST"])
def assign_user():
    data       = request.get_json()
    project_name = data.get("projectName")  # Changed from projectId to projectName
    user_id    = data.get("userId")
    role       = data.get("role")  # This will be the role to assign for the project (developer/auditor)

    if role not in ("developer", "auditor"):
        return jsonify({"error": "Invalid role"}), 400

    if not all([project_name, user_id, role]):
        return jsonify({"error": "Missing data"}), 400

    try:
        # verify user exists and has the appropriate role
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user has appropriate role (developer or auditor)
        if user.get("role") not in ["developer", "auditor"]:
            return jsonify({"error": "User must be a developer or auditor"}), 400

        # check duplicate assignment in user's assignedProjects
        user_assigned_projects = user.get("assignedProjects", [])
        if any(p.get("projectName") == project_name for p in user_assigned_projects):
            return jsonify({"error": "User already assigned to this project"}), 409

        # Add project to user's assignedProjects array
        project_assignment = {
            "projectName": project_name,
            "role": role,  # Role for this specific project
            "assignedAt": data.get("assignedAt") or "2025-01-01T00:00:00Z"
        }
        
        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"assignedProjects": project_assignment}}
        )
        
        return jsonify({"message": "User assigned successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- POST /remove_user_from_project ----------
@admin_bp.route("/remove_user_from_project", methods=["POST"])
def remove_user_from_project():
    """Remove a user from a project"""
    data = request.get_json()
    project_name = data.get("projectName")  # Changed from projectId to projectName
    user_id = data.get("userId")

    if not all([project_name, user_id]):
        return jsonify({"error": "Missing projectName or userId"}), 400

    try:
        # verify user exists
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user is assigned to this project
        user_assigned_projects = user.get("assignedProjects", [])
        if not any(p.get("projectName") == project_name for p in user_assigned_projects):
            return jsonify({"error": "User not assigned to this project"}), 404

        # Remove project from user's assignedProjects array
        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"assignedProjects": {"projectName": project_name}}}
        )
        
        return jsonify({"message": "User removed from project successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- GET /user_projects/<user_id> ----------
@admin_bp.route("/user_projects/<user_id>", methods=["GET"])
def get_user_projects(user_id):
    """Get all projects assigned to a specific user from their assignedProjects array"""
    try:
        # Find the user and get their assigned projects
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        assigned_projects = user.get("assignedProjects", [])
        
        # Format the project data for response
        projects = []
        for project_assignment in assigned_projects:
            project = {
                "_id": project_assignment.get("projectName"),  # Use project name as ID
                "name": project_assignment.get("projectName"),
                "userRole": project_assignment.get("role"),  # User's role for this project
                "assignedAt": project_assignment.get("assignedAt")
            }
            projects.append(project)
        
        return jsonify({"projects": projects}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500