from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from config.db import connect_db

db = connect_db()
admin_bp = Blueprint('admin', __name__)
users_col = db['users']
projects_col = db['projects']
access_col = db['access_requests']

@admin_bp.route('/users', methods=['GET'])
def get_users():
    try:
        users = list(users_col.find({'role': {'$in': ['developer', 'auditor']}}, {'password': 0}))
        for user in users:
            user['_id'] = str(user['_id'])
        return jsonify({'users': users}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/available_users', methods=['GET'])
def get_available_users():
    try:
        users = list(users_col.find({'role': {'$in': ['developer', 'auditor']}}, {
            '_id': 1, 'username': 1, 'githubUsername': 1, 'role': 1, 'email': 1
        }))
        for user in users:
            user['_id'] = str(user['_id'])
        return jsonify({'users': users}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route("/create_project", methods=["POST"])
def create_project():
    data = request.get_json()
    name        = data.get("name")
    admin_gh    = data.get("adminGithubUsername")

    if not all([name, admin_gh]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # ✅ Use users_col instead of undefined users
        result = users_col.update_one(
            {"githubUsername": admin_gh},
            {"$addToSet": {"createdProjects": name}}  # Prevents duplicates
        )
        if result.matched_count == 0:
            return jsonify({"error": "Admin user not found"}), 404
        
        return jsonify({"message": "Project created successfully"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/update_project', methods=['PUT'])
def update_project():
    data = request.get_json() or {}

    name = data.get('name')
    if not name:
        return jsonify({'error': 'Project name required'}), 400

    # Fields to update in the specific project object inside createdProjects array
    fields_to_update = {k: v for k, v in data.items() if k != 'name'}
    if not fields_to_update:
        return jsonify({'error': 'No fields to update'}), 400

    try:
        # Find the admin who has created this project
        admin_user = users_col.find_one({"createdProjects": name})
        if not admin_user:
            return jsonify({"error": "Admin user with this project not found"}), 404

        github_username = admin_user.get("githubUsername")
        if not github_username:
            return jsonify({"error": "Admin user does not have GitHub username"}), 500

        # Update the project object inside the admin's createdProjects array
        result = users_col.update_one(
            {
                "githubUsername": github_username,
                "createdProjects": name
            },
            {
                "$set": {
                    **{f"projectMetadata.{name}.{k}": v for k, v in fields_to_update.items()}
                }
            }
        )

        return jsonify({"message": "Project metadata updated"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/commits/<github_username>', methods=['GET'])
def admin_projects(github_username):
    try:
        admin_user = users_col.find_one({'githubUsername': github_username})
        if not admin_user:
            return jsonify({'error': 'Admin user not found'}), 404
        created_projects = admin_user.get('createdProjects', [])
        projects = []
        for project_name in created_projects:
            assigned_users = []
            users_with_project = users_col.find({'assignedProjects.projectName': project_name})
            for user in users_with_project:
                user_projects = user.get('assignedProjects', [])
                for project_assignment in user_projects:
                    if project_assignment.get('projectName') == project_name:
                        assigned_users.append({
                            'userId': str(user['_id']),
                            'username': user.get('username'),
                            'githubUsername': user.get('githubUsername'),
                            'role': project_assignment.get('role'),
                            'assignedAt': project_assignment.get('assignedAt')
                        })
                        break
            project = {
                '_id': project_name,
                'name': project_name,
                'assignedUsers': assigned_users,
                'adminGithubUsername': github_username
            }
            projects.append(project)
        return jsonify({'projects': projects}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/assign_user_to_project', methods=['POST'])
def assign_user():
    data = request.get_json()
    project_name = data.get('projectName')
    user_id = data.get('userId')
    role = data.get('role')
    if role not in ('developer', 'auditor'):
        return jsonify({'error': 'Invalid role'}), 400
    if not all([project_name, user_id, role]):
        return jsonify({'error': 'Missing data'}), 400
    try:
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if user.get('role') not in ['developer', 'auditor']:
            return jsonify({'error': 'User must be a developer or auditor'}), 400
        user_assigned_projects = user.get('assignedProjects', [])
        if any(p.get('projectName') == project_name for p in user_assigned_projects):
            return jsonify({'error': 'User already assigned to this project'}), 409
        project_assignment = {
            'projectName': project_name,
            'role': role,
            'assignedAt': data.get('assignedAt') or '2025-01-01T00:00:00Z'
        }
        users_col.update_one({'_id': ObjectId(user_id)}, {'$push': {'assignedProjects': project_assignment}})
        return jsonify({'message': 'User assigned successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/remove_user_from_project', methods=['POST'])
def remove_user_from_project():
    data = request.get_json()
    project_name = data.get('projectName')
    user_id = data.get('userId')
    if not all([project_name, user_id]):
        return jsonify({'error': 'Missing projectName or userId'}), 400
    try:
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_assigned_projects = user.get('assignedProjects', [])
        if not any(p.get('projectName') == project_name for p in user_assigned_projects):
            return jsonify({'error': 'User not assigned to this project'}), 404
        users_col.update_one({'_id': ObjectId(user_id)},
                             {'$pull': {'assignedProjects': {'projectName': project_name}}})
        return jsonify({'message': 'User removed from project successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user_projects/<user_id>', methods=['GET'])
def get_user_projects(user_id):
    try:
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        assigned_projects = user.get('assignedProjects', [])
        projects = []
        for project_assignment in assigned_projects:
            project = {
                '_id': project_assignment.get('projectName'),
                'name': project_assignment.get('projectName'),
                'userRole': project_assignment.get('role'),
                'assignedAt': project_assignment.get('assignedAt')
            }
            projects.append(project)
        return jsonify({'projects': projects}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
