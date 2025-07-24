from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from config.db import connect_db
import requests

db = connect_db()
admin_bp = Blueprint('admin', __name__)
users_col = db['users']
projects_col = db['projects']
access_col = db['access_requests']

def serialize_user(doc, mask=True):
    data = {
        'id': str(doc['_id']),
        'username': doc['username'],
        'email': doc['email'],
        'role': doc['role'],
        'githubUsername': doc.get('githubUsername', ''),
        'points': doc.get('points', {}) if doc['role'] == 'developer' else None  # Use object for points
    }
    token = doc.get('githubToken', '')
    if mask and len(token) >= 8:
        token = token[:4] + '*' * (len(token) - 8) + token[-4:]
    data['githubToken'] = token
    if doc['role'] == 'admin':
        data['createdProjects'] = doc.get('createdProjects', [])
    else:
        data['assignedProjects'] = doc.get('assignedProjects', [])
    return data

@admin_bp.route('/users', methods=['GET'])
def get_users():
    try:
        users = list(users_col.find({'role': {'$in': ['developer', 'auditor']}}, {'password': 0, '_id': 1, 'username': 1, 'email': 1, 'role': 1, 'githubUsername': 1, 'points': 1}))
        for user in users:
            user['_id'] = str(user['_id'])
        print(f"Retrieved {len(users)} users")
        return jsonify({'users': users}), 200
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/available_users', methods=['GET'])
def get_available_users():
    try:
        users = list(users_col.find({'role': {'$in': ['developer', 'auditor']}}, {
            '_id': 1, 'username': 1, 'githubUsername': 1, 'role': 1, 'email': 1, 'points': 1
        }))
        for user in users:
            user['_id'] = str(user['_id'])
        print(f"Retrieved {len(users)} available users")
        return jsonify({'users': users}), 200
    except Exception as e:
        print(f"Error fetching available users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        project_name = request.args.get('project')
        query = {'role': 'developer'}
        if project_name:
            query['assignedProjects.projectName'] = project_name
        developers = list(users_col.find(
            query,
            {'_id': 1, 'username': 1, 'githubUsername': 1, 'points': 1, 'assignedProjects': 1}
        ).sort('points.' + project_name if project_name else 'points', -1))
        for dev in developers:
            dev['_id'] = str(dev['_id'])
            if project_name and dev.get('points'):
                dev['points'] = dev['points'].get(project_name, 0)
        print(f"Retrieved leaderboard for project: {project_name or 'all'}")
        return jsonify({'developers': developers}), 200
    except Exception as e:
        print(f"Error fetching leaderboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route("/create_project", methods=["POST"])
def create_project():
    data = request.get_json() or {}
    name = data.get("name")
    admin_gh = data.get("adminGithubUsername")

    if not all([name, admin_gh]):
        print(f"Missing fields: name={name}, admin_gh={admin_gh}")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        admin_user = users_col.find_one({"githubUsername": admin_gh})
        if not admin_user:
            print(f"Admin not found: {admin_gh}")
            return jsonify({"error": "Admin user not found"}), 404

        github_token = admin_user.get('githubToken')
        repo_check_url = f"https://api.github.com/repos/{admin_gh}/{name}"
        response = requests.get(
            repo_check_url,
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github+json"
            }
        )
        if response.status_code != 200:
            print(f"GitHub repo check failed: {response.status_code} - {response.text}")
            return jsonify({"error": "Repository does not exist or is inaccessible"}), 404

        result = users_col.update_one(
            {"githubUsername": admin_gh},
            {"$addToSet": {"createdProjects": name}}
        )
        if result.matched_count == 0:
            print(f"Admin not found for update: {admin_gh}")
            return jsonify({"error": "Admin user not found"}), 404
        
        print(f"Created project {name} for admin {admin_gh}")
        return jsonify({"message": "Project created successfully"}), 201
    
    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/update_project', methods=['PUT'])
def update_project():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        print("Missing project name")
        return jsonify({'error': 'Project name required'}), 400

    fields_to_update = {k: v for k, v in data.items() if k != 'name'}
    if not fields_to_update:
        print("No fields to update")
        return jsonify({'error': 'No fields to update'}), 400

    try:
        admin_user = users_col.find_one({"createdProjects": name})
        if not admin_user:
            print(f"Admin not found for project: {name}")
            return jsonify({"error": "Admin user with this project not found"}), 404

        github_username = admin_user.get("githubUsername")
        if not github_username:
            print(f"No githubUsername for admin of project: {name}")
            return jsonify({"error": "Admin user does not have GitHub username"}), 500

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
        if result.matched_count == 0:
            print(f"No matching admin found for project: {name}")
            return jsonify({"error": "No matching admin found"}), 404

        print(f"Updated metadata for project: {name}")
        return jsonify({"message": "Project metadata updated"}), 200

    except Exception as e:
        print(f"Error updating project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/commits/<github_username>', methods=['GET'])
def admin_projects(github_username):
    try:
        admin_user = users_col.find_one({'githubUsername': github_username})
        if not admin_user:
            print(f"Admin not found: {github_username}")
            return jsonify({'error': 'Admin user not found'}), 404
        created_projects = admin_user.get('createdProjects', [])
        projects = []
        for project_name in created_projects:
            if not isinstance(project_name, str) or not project_name.strip():
                print(f"Invalid project name: {project_name}")
                continue
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
                            'assignedAt': project_assignment.get('assignedAt'),
                            'points': user.get('points', {}).get(project_name, 0) if user.get('role') == 'developer' else None
                        })
                        break
            project = {
                '_id': project_name,
                'name': project_name,
                'assignedUsers': assigned_users,
                'adminGithubUsername': github_username
            }
            projects.append(project)
        print(f"Retrieved {len(projects)} projects for admin {github_username}")
        return jsonify({'projects': projects}), 200
    except Exception as e:
        print(f"Error fetching projects for {github_username}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/assign_user_to_project', methods=['POST'])
def assign_user():
    data = request.get_json() or {}
    project_name = data.get('projectName')
    user_id = data.get('userId')
    role = data.get('role')
    if not project_name or not isinstance(project_name, str) or not project_name.strip():
        print(f"Invalid projectName: {project_name}")
        return jsonify({'error': 'Invalid or missing project name'}), 400
    if role not in ('developer', 'auditor'):
        print(f"Invalid role: {role}")
        return jsonify({'error': 'Invalid role'}), 400
    if not all([project_name, user_id, role]):
        print(f"Missing data: projectName={project_name}, userId={user_id}, role={role}")
        return jsonify({'error': 'Missing data'}), 400
    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            print(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        if user.get('role') not in ['developer', 'auditor']:
            print(f"User role invalid: {user.get('role')}")
            return jsonify({'error': 'User must be a developer or auditor'}), 400
        user_assigned_projects = user.get('assignedProjects', [])
        if any(p.get('projectName') == project_name for p in user_assigned_projects):
            print(f"User {user_id} already assigned to project {project_name}")
            return jsonify({'error': 'User already assigned to this project'}), 409
        project_assignment = {
            'projectName': project_name,
            'role': role,
            'assignedAt': data.get('assignedAt') or '2025-01-01T00:00:00Z'
        }
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$push': {'assignedProjects': project_assignment}}
        )
        if role == 'developer':
            users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {f'points.{project_name}': 0}}
            )
        print(f"Assigned user {user_id} to project {project_name} as {role}")
        return jsonify({'message': 'User assigned successfully'}), 200
    except Exception as e:
        print(f"Error assigning user to project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/remove_user_from_project', methods=['POST'])
def remove_user_from_project():
    data = request.get_json() or {}
    project_name = data.get('projectName')
    user_id = data.get('userId')
    if not project_name or not isinstance(project_name, str) or not project_name.strip():
        print(f"Invalid projectName: {project_name}")
        return jsonify({'error': 'Invalid or missing project name'}), 400
    if not all([project_name, user_id]):
        print(f"Missing data: projectName={project_name}, userId={user_id}")
        return jsonify({'error': 'Missing projectName or userId'}), 400
    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            print(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        user_assigned_projects = user.get('assignedProjects', [])
        if not any(p.get('projectName') == project_name for p in user_assigned_projects):
            print(f"User {user_id} not assigned to project {project_name}")
            return jsonify({'error': 'User not assigned to this project'}), 404
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$pull': {'assignedProjects': {'projectName': project_name}}}
        )
        if user.get('role') == 'developer':
            users_col.update_one(
                {'_id': ObjectId(user_id)},
                {'$unset': {f'points.{project_name}': ''}}
            )
        print(f"Removed user {user_id} from project {project_name}")
        return jsonify({'message': 'User removed from project successfully'}), 200
    except Exception as e:
        print(f"Error removing user from project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user_projects/<user_id>', methods=['GET'])
def get_user_projects(user_id):
    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            print(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        assigned_projects = user.get('assignedProjects', [])
        projects = []
        for project_assignment in assigned_projects:
            if not project_assignment.get('projectName') or not isinstance(project_assignment.get('projectName'), str):
                print(f"Invalid project in assignedProjects: {project_assignment}")
                continue
            project = {
                '_id': project_assignment.get('projectName'),
                'name': project_assignment.get('projectName'),
                'userRole': project_assignment.get('role'),
                'assignedAt': project_assignment.get('assignedAt')
            }
            projects.append(project)
        print(f"Retrieved {len(projects)} projects for user {user_id}")
        return jsonify({'projects': projects}), 200
    except Exception as e:
        print(f"Error fetching projects for user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500