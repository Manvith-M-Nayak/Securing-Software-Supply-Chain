from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from config.db import connect_db
import requests
from web3 import Web3
import os
import json
import base64
import shutil
import subprocess

db = connect_db()
admin_bp = Blueprint('admin', __name__)
users_col = db['users']
projects_col = db['projects']
access_col = db['access_requests']

# def serialize_user(doc, mask=True):
#     data = {
#         'id': str(doc['_id']),
#         'username': doc['username'],
#         'email': doc['email'],
#         'role': doc['role'],
#         'githubUsername': doc.get('githubUsername', ''),
#         'points': doc.get('points', {}) if doc['role'] == 'developer' else None  # Use object for points
#     }
#     token = doc.get('githubToken', '')
#     if mask and len(token) >= 8:
#         token = token[:4] + '*' * (len(token) - 8) + token[-4:]
#     data['githubToken'] = token
#     if doc['role'] == 'admin':
#         data['createdProjects'] = doc.get('createdProjects', [])
#     else:
#         data['assignedProjects'] = doc.get('assignedProjects', [])
#     return data

# @admin_bp.route('/users', methods=['GET'])
# def get_users():
#     try:
#         users = list(users_col.find({'role': {'$in': ['developer', 'auditor']}}, {'password': 0, '_id': 1, 'username': 1, 'email': 1, 'role': 1, 'githubUsername': 1, 'points': 1}))
#         for user in users:
#             user['_id'] = str(user['_id'])
#         print(f"Retrieved {len(users)} users")
#         return jsonify({'users': users}), 200
#     except Exception as e:
#         print(f"Error fetching users: {str(e)}")
#         return jsonify({'error': str(e)}), 500

# @admin_bp.route('/leaderboard', methods=['GET'])
# def get_leaderboard():
#     try:
#         project_name = request.args.get('project')
#         query = {'role': 'developer'}
#         if project_name:
#             query['assignedProjects.projectName'] = project_name
#         developers = list(users_col.find(
#             query,
#             {'_id': 1, 'username': 1, 'githubUsername': 1, 'points': 1, 'assignedProjects': 1}
#         ).sort('points.' + project_name if project_name else 'points', -1))
#         for dev in developers:
#             dev['_id'] = str(dev['_id'])
#             if project_name and dev.get('points'):
#                 dev['points'] = dev['points'].get(project_name, 0)
#         print(f"Retrieved leaderboard for project: {project_name or 'all'}")
#         return jsonify({'developers': developers}), 200
#     except Exception as e:
#         print(f"Error fetching leaderboard: {str(e)}")
#         return jsonify({'error': str(e)}), 500

# This is for creating a new project
@admin_bp.route("/create_project", methods=["POST"])
def create_project():
    data = request.get_json() or {}
    name = data.get("name")
    admin_gh = data.get("adminGithubUsername")
    created_at = data.get("createdAt")

    # Validate required fields
    if not all([name, admin_gh, created_at]):
        print(f"Missing fields: name={name}, admin_gh={admin_gh}, created_at={created_at}")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Check if admin user exists
        admin_user = db['users'].find_one({"githubUsername": admin_gh})
        if not admin_user:
            print(f"Admin not found: {admin_gh}")
            return jsonify({"error": "Admin user not found"}), 404

        # Check if project already exists for this admin to avoid duplicates
        if db['users'].find_one({"githubUsername": admin_gh, "createdProjects": name}):
            print(f"Project already exists: {name} for admin {admin_gh}")
            return jsonify({"error": "Project already exists"}), 400

        # Add project to admin's createdProjects array and initialize projectMetadata
        result = db['users'].update_one(
            {"githubUsername": admin_gh},
            {
                "$addToSet": {"createdProjects": name},
                "$set": {f"projectMetadata.{name}": {}}
            }
        )
        if result.matched_count == 0:
            print(f"Admin not found for update: {admin_gh}")
            return jsonify({"error": "Admin user not found"}), 404

        # Store project details in a separate projects collection
        projects_col = db['projects']
        project_data = {
            "name": name,
            "adminGithubUsername": admin_gh,
            "createdAt": created_at,
            "githubRepoUrl": None,
            "githubRepoId": None,
            "webhookId": None,
            "webhookUrl": None
        }
        projects_col.insert_one(project_data)

        print(f"Created project {name} for admin {admin_gh}")
        return jsonify({"message": "Project created successfully"}), 201

    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/update_project", methods=["PUT"])
def update_project():
    data = request.get_json() or {}
    name = data.get("name")
    github_repo_url = data.get("githubRepoUrl")
    github_repo_id = data.get("githubRepoId")
    webhook_id = data.get("webhookId")
    webhook_url = data.get("webhookUrl")

    if not all([name, github_repo_url, github_repo_id, webhook_id, webhook_url]):
        print(f"Missing fields in update: name={name}, github_repo_url={github_repo_url}")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Update project in projects collection
        projects_col = db['projects']
        project_result = projects_col.update_one(
            {"name": name},
            {
                "$set": {
                    "githubRepoUrl": github_repo_url,
                    "githubRepoId": github_repo_id,
                    "webhookId": webhook_id,
                    "webhookUrl": webhook_url
                }
            }
        )
        if project_result.matched_count == 0:
            print(f"Project not found for update: {name}")
            return jsonify({"error": "Project not found"}), 404

        # Update projectMetadata in users collection
        user_result = db['users'].update_one(
            {"createdProjects": name},
            {
                "$set": {
                    f"projectMetadata.{name}": {
                        "githubRepoId": github_repo_id,
                        "githubRepoUrl": github_repo_url,
                        "webhookId": webhook_id,
                        "webhookUrl": webhook_url
                    }
                }
            }
        )
        if user_result.matched_count == 0:
            print(f"User with project not found for update: {name}")
            return jsonify({"error": "User with project not found"}), 404

        print(f"Updated project {name}")
        return jsonify({"message": "Project updated successfully"}), 200

    except Exception as e:
        print(f"Error updating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

# @admin_bp.route('/commits/<github_username>', methods=['GET'])
# def admin_projects(github_username):
#     try:
#         admin_user = users_col.find_one({'githubUsername': github_username})
#         if not admin_user:
#             print(f"Admin not found: {github_username}")
#             return jsonify({'error': 'Admin user not found'}), 404
#         created_projects = admin_user.get('createdProjects', [])
#         projects = []
#         for project_name in created_projects:
#             if not isinstance(project_name, str) or not project_name.strip():
#                 print(f"Invalid project name: {project_name}")
#                 continue
#             assigned_users = []
#             users_with_project = users_col.find({'assignedProjects.projectName': project_name})
#             for user in users_with_project:
#                 user_projects = user.get('assignedProjects', [])
#                 for project_assignment in user_projects:
#                     if project_assignment.get('projectName') == project_name:
#                         assigned_users.append({
#                             'userId': str(user['_id']),
#                             'username': user.get('username'),
#                             'githubUsername': user.get('githubUsername'),
#                             'role': project_assignment.get('role'),
#                             'assignedAt': project_assignment.get('assignedAt'),
#                             'points': user.get('points', {}).get(project_name, 0) if user.get('role') == 'developer' else None
#                         })
#                         break
#             project = {
#                 '_id': project_name,
#                 'name': project_name,
#                 'assignedUsers': assigned_users,
#                 'adminGithubUsername': github_username
#             }
#             projects.append(project)
#         print(f"Retrieved {len(projects)} projects for admin {github_username}")
#         return jsonify({'projects': projects}), 200
#     except Exception as e:
#         print(f"Error fetching projects for {github_username}: {str(e)}")
#         return jsonify({'error': str(e)}), 500


@admin_bp.route('/available_users', methods=['GET'])
def get_available_users():
    try:
        users = list(users_col.find(
            {'role': {'$in': ['developer', 'auditor']}},
            {'_id': 1, 'username': 1, 'githubUsername': 1, 'role': 1, 'email': 1, 'points': 1}
        ))
        for user in users:
            user['_id'] = str(user['_id'])
        print(f"Retrieved {len(users)} available users")
        return jsonify({'users': users}), 200
    except Exception as e:
        print(f"Error fetching available users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/projects/<github_username>', methods=['GET'])
def get_admin_projects(github_username):
    try:
        # Find the admin user
        admin = users_col.find_one({'githubUsername': github_username})
        if not admin:
            print(f"Admin not found: {github_username}")
            return jsonify({'error': 'Admin user not found'}), 404

        # Get projects from createdProjects and projectMetadata
        created_projects = admin.get('createdProjects', [])
        project_metadata = admin.get('projectMetadata', {})
        projects = []
        for project_name in created_projects:
            metadata = project_metadata.get(project_name, {})
            # Fetch assigned users for this project
            assigned_users = []
            for user in users_col.find({'assignedProjects.projectName': project_name}):
                for assignment in user.get('assignedProjects', []):
                    if assignment['projectName'] == project_name:
                        assigned_users.append({
                            'userId': str(user['_id']),
                            'username': user.get('username', user.get('email', 'Unknown')),
                            'githubUsername': user.get('githubUsername', ''),
                            'role': assignment['role'],
                            'assignedAt': assignment.get('assignedAt'),
                            'points': user.get('points', {}).get(project_name)
                        })
            projects.append({
                '_id': project_name,  # Use project name as ID for frontend compatibility
                'name': project_name,
                'githubRepoId': metadata.get('githubRepoId'),
                'githubRepoUrl': metadata.get('githubRepoUrl'),
                'webhookId': metadata.get('webhookId'),
                'webhookUrl': metadata.get('webhookUrl'),
                'assignedUsers': assigned_users
            })

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
    assigned_at = data.get('assignedAt')

    if not project_name or not isinstance(project_name, str) or not project_name.strip():
        print(f"Invalid projectName: {project_name}")
        return jsonify({'error': 'Invalid or missing project name'}), 400
    if role not in ('developer', 'auditor'):
        print(f"Invalid role: {role}")
        return jsonify({'error': 'Invalid role'}), 400
    if not all([project_name, user_id, role, assigned_at]):
        print(f"Missing data: projectName={project_name}, userId={user_id}, role={role}, assignedAt={assigned_at}")
        return jsonify({'error': 'Missing required fields'}), 400

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

        # Check if project exists in any admin's createdProjects
        admin = users_col.find_one({'createdProjects': project_name})
        if not admin:
            print(f"Project not found: {project_name}")
            return jsonify({'error': 'Project not found'}), 404

        # Check if user is already assigned to the project
        user_assigned_projects = user.get('assignedProjects', [])
        if any(p.get('projectName') == project_name for p in user_assigned_projects):
            print(f"User {user_id} already assigned to project {project_name}")
            return jsonify({'error': 'User already assigned to this project'}), 409

        # Assign user to project
        project_assignment = {
            'projectName': project_name,
            'role': role,
            'assignedAt': assigned_at
        }
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$push': {'assignedProjects': project_assignment}}
        )

        # Initialize points for developer
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

        # Check if user is assigned to the project
        user_assigned_projects = user.get('assignedProjects', [])
        if not any(p.get('projectName') == project_name for p in user_assigned_projects):
            print(f"User {user_id} not assigned to project {project_name}")
            return jsonify({'error': 'User not assigned to this project'}), 404

        # Remove user from project
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$pull': {'assignedProjects': {'projectName': project_name}}}
        )

        # Remove points for developer
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

# @admin_bp.route('/user_projects/<user_id>', methods=['GET'])
# def get_user_projects(user_id):
#     try:
#         if not ObjectId.is_valid(user_id):
#             print(f"Invalid user_id: {user_id}")
#             return jsonify({'error': 'Invalid user ID format'}), 400
#         user = users_col.find_one({'_id': ObjectId(user_id)})
#         if not user:
#             print(f"User not found: {user_id}")
#             return jsonify({'error': 'User not found'}), 404
#         assigned_projects = user.get('assignedProjects', [])
#         projects = []
#         for project_assignment in assigned_projects:
#             if not project_assignment.get('projectName') or not isinstance(project_assignment.get('projectName'), str):
#                 print(f"Invalid project in assignedProjects: {project_assignment}")
#                 continue
#             project = {
#                 '_id': project_assignment.get('projectName'),
#                 'name': project_assignment.get('projectName'),
#                 'userRole': project_assignment.get('role'),
#                 'assignedAt': project_assignment.get('assignedAt')
#             }
#             projects.append(project)
#         print(f"Retrieved {len(projects)} projects for user {user_id}")
#         return jsonify({'projects': projects}), 200
#     except Exception as e:
#         print(f"Error fetching projects for user {user_id}: {str(e)}")
#         return jsonify({'error': str(e)}), 500

w3 = Web3(Web3.HTTPProvider(os.getenv('GANACHE_RPC')))
contract_address = os.getenv('PULLREQUESTS_ADDRESS', '0xbA23583659a1a57b495211Ad3989983Aa7D47253')

with open(os.path.join(os.path.dirname(__file__), '../abis/PullRequests.json'), 'r') as f:
    contract_abi = json.load(f)['abi']
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

def check_vulnerabilities(file_content, filename):
    """Run Bearer CLI to scan .py files for vulnerabilities."""
    if not filename.endswith('.py'):
        return {"is_vulnerable": False, "details": "Non-Python file, marked as safe"}

    if not file_content or file_content.strip() == "":
        print(f"No content to scan for {filename}: content is empty or whitespace")
        return {"is_vulnerable": False, "details": "Empty or invalid file content"}

    content_to_scan = file_content
    print(f"Preparing to scan content for {filename}: {content_to_scan[:100]}{'...' if len(content_to_scan) > 100 else ''}")

    bearer_path = shutil.which('bearer') or '/usr/local/bin/bearer'
    if not os.path.exists(bearer_path):
        print(f"Bearer CLI not found at {bearer_path}")
        return {"is_vulnerable": False, "details": "Bearer CLI not installed or not found"}

    vulnerabilities = []
    temp_file_path = None
    stderr_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(content_to_scan)
            temp_file_path = temp_file.name

        # Verify temporary file content
        with open(temp_file_path, 'r', encoding='utf-8') as temp_file:
            temp_content = temp_file.read()
            print(f"Temporary file content for {filename}: {temp_content[:100]}{'...' if len(temp_content) > 100 else ''}")

        stderr_fd, stderr_file_path = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(stderr_fd, 'w') as stderr_file:
            stderr_file.write("")

        result = subprocess.run(
            [bearer_path, 'scan', temp_file_path, '--format', 'json', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )

        with open(stderr_file_path, 'r', encoding='utf-8') as stderr_file:
            stderr_output = stderr_file.read()

        print(f"Bearer scan stdout for {filename}: {result.stdout}")
        print(f"Bearer scan stderr for {filename}: {stderr_output}")
        print(f"Bearer scan return code for {filename}: {result.returncode}")

        if result.stdout:
            try:
                bearer_output = json.loads(result.stdout)
                if not bearer_output:  # Empty JSON output
                    print(f"Empty Bearer scan output for {filename}: likely no vulnerabilities in simple Python code")
                    return {"is_vulnerable": False, "details": "No vulnerabilities detected (simple Python code)"}
                for severity in ['critical', 'high', 'medium', 'low', 'warning']:
                    for finding in bearer_output.get(severity, []):
                        vulnerabilities.append({
                            "type": finding.get('title', 'Unknown Vulnerability'),
                            "line": finding.get('line_number', 1),
                            "snippet": finding.get('code_extract', finding.get('snippet', 'No snippet available'))
                        })
            except json.JSONDecodeError as e:
                print(f"Failed to parse Bearer JSON output for {filename}: {str(e)}")
                return {"is_vulnerable": False, "details": f"Failed to parse Bearer output: {str(e)}"}

        if not vulnerabilities and stderr_output:
            print(f"Bearer scan error for {filename}: {stderr_output}")
            return {"is_vulnerable": False, "details": f"Bearer scan failed: {stderr_output}"}
        elif not vulnerabilities and not result.stdout:
            print(f"Bearer scan produced no output for {filename}")
            return {"is_vulnerable": False, "details": "No vulnerabilities detected (no scan output)"}

    except subprocess.TimeoutExpired:
        print(f"Bearer scan timed out for {filename}")
        return {"is_vulnerable": False, "details": "Bearer scan timed out"}
    except Exception as e:
        print(f"Error running Bearer scan for {filename}: {str(e)}")
        return {"is_vulnerable": False, "details": f"Failed to scan file: {str(e)}"}
    finally:
        for path in [temp_file_path, stderr_file_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    print(f"Failed to delete temporary file {path}: {str(e)}")

    if vulnerabilities:
        return {"is_vulnerable": True, "details": vulnerabilities}
    return {"is_vulnerable": False, "details": "No vulnerabilities detected"}

@admin_bp.route("/pull_requests/<project_name>", methods=["GET"])
def get_pull_requests(project_name):
    print(f"Entering get_pull_requests endpoint for project: {project_name}")
    user_email = request.headers.get("X-User-Email")
    print(f"User email: {user_email}")
    user = db.users.find_one({"email": user_email, "role": "admin"})
    if not user:
        print(f"No admin found for email: {user_email}")
        return jsonify({"error": "No admin found"}), 404

    if not project_name:
        print("Project name is missing")
        return jsonify({"error": "Project name is required"}), 400

    created_projects = user.get("createdProjects", [])
    print(f"Created projects: {created_projects}")
    if project_name not in created_projects:
        print(f"Project {project_name} not created by user")
        return jsonify({"error": "Project not created by user"}), 403

    github_token = user.get("githubToken", "")
    repo_owner = user.get("githubUsername", "")
    print(f"Admin GitHub username: {repo_owner}, token present: {bool(github_token)}")
    if not github_token or not repo_owner:
        print("Admin GitHub credentials missing")
        return jsonify({"error": "Admin GitHub credentials missing", "project": project_name}), 400

    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    pullrequests = []
    approved_count = 0
    rejected_count = 0
    try:
        repo_check_url = f"https://api.github.com/repos/{repo_owner}/{project_name}"
        print(f"Checking repository: {repo_check_url}")
        repo_response = requests.get(repo_check_url, headers=headers)
        print(f"Repository check response: status={repo_response.status_code}")
        if repo_response.status_code == 404:
            print(f"Repository not found: {project_name}")
            return jsonify({"error": f"Repository {project_name} not found"}), 404
        elif repo_response.status_code == 403:
            print(f"Rate limit exceeded checking repository {project_name}: {repo_response.status_code} - {repo_response.text}")
            return jsonify({"error": "GitHub API rate limit exceeded"}), 403

        repo_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls?state=all"
        print(f"Fetching pull requests from: {repo_url}")
        response = requests.get(repo_url, headers=headers)
        print(f"GitHub API response for {project_name}: status={response.status_code}, data={response.text[:200]}...")

        if response.status_code == 200:
            prs = response.json()
            print(f"Found {len(prs)} pull requests")
            for pr in prs:
                pr_id = int(pr["number"])
                developer = (pr["user"]["login"] or "").lower().strip()
                print(f"Processing PR #{pr_id}, developer: {developer}")

                files_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pr_id}/files"
                print(f"Fetching files for PR #{pr_id}: {files_url}")
                files_response = requests.get(files_url, headers=headers)
                changed_files = []

                if files_response.status_code == 200:
                    files_data = files_response.json()
                    print(f"Found {len(files_data)} files in PR #{pr_id}")
                    for file in files_data:
                        file_content = None
                        if "contents_url" in file:
                            print(f"Fetching file content: {file['contents_url']}")
                            content_response = requests.get(file["contents_url"], headers=headers)
                            if content_response.status_code == 200:
                                content_data = content_response.json()
                                if "content" in content_data and content_data.get("encoding") == "base64":
                                    try:
                                        file_content = base64.b64decode(content_data["content"]).decode('utf-8', errors='replace')
                                    except (base64.binascii.Error, UnicodeDecodeError) as e:
                                        print(f"Error decoding file content: {str(e)}")
                                        file_content = file.get("patch", "No content available")
                        if not file_content:
                            file_content = file.get("patch", "No content available")
                            print(f"Using patch as file content for {file['filename']}")

                        vuln_result = check_vulnerabilities(file_content, file["filename"])
                        changed_files.append({
                            "filename": file["filename"],
                            "content": file_content,
                            "vulnerability": vuln_result
                        })
                        print(f"File {file['filename']} processed, vulnerability: {vuln_result['is_vulnerable']}")

                pr_status = "approved" if pr.get("merged_at") else ("rejected" if pr["state"] == "closed" else "pending")
                if pr_status == "approved":
                    approved_count += 1
                elif pr_status == "rejected":
                    rejected_count += 1
                pr_data = {
                    "pullRequestId": str(pr_id),
                    "projectName": project_name,
                    "developer": developer,
                    "timestamp": pr["created_at"],
                    "status": pr_status,
                    "changedFiles": changed_files,
                    "securityScore": None if any(f["vulnerability"]["is_vulnerable"] for f in changed_files) else "Safe",
                    "txHash": "N/A"
                }
                print(f"PR #{pr_id} data prepared: status={pr_status}, files={len(changed_files)}")

                # Check if PR exists on blockchain with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        pr_on_chain = contract.functions.getPullRequest(pr_id).call()
                        print(f"PR #{pr_id} blockchain check: isLogged={pr_on_chain[5]}")
                        if pr_on_chain[5]:  # isLogged
                            events = contract.events.PullRequestLogged.get_logs(
                                fromBlock=0,
                                argument_filters={'pullRequestId': pr_id}
                            )
                            if events:
                                latest_event = max(events, key=lambda e: e['blockNumber'])
                                pr_data["txHash"] = latest_event['transactionHash'].hex()
                                print(f"PR #{pr_id} already logged, txHash: {pr_data['txHash']}")
                            break
                        else:
                            print(f"Logging new PR #{pr_id} to blockchain")
                            balance = w3.eth.get_balance(blockchain_account.address)
                            balance_eth = w3.from_wei(balance, 'ether')
                            print(f"Account {blockchain_account.address} balance: {balance_eth} ETH")
                            if balance_eth < 0.01:
                                print(f"Insufficient balance for PR #{pr_id}: {balance_eth} ETH")
                                return jsonify({"error": f"Insufficient account balance: {balance_eth} ETH"}), 500

                            nonce = w3.eth.get_transaction_count(blockchain_account.address, 'pending')
                            gas_estimate = contract.functions.logPullRequest(
                                pr_id, project_name, developer, pr["created_at"], pr_status
                            ).estimate_gas({'from': blockchain_account.address})
                            print(f"PR #{pr_id} gas estimate: {gas_estimate}, using gas: {gas_estimate + 10000}")
                            gas_price = w3.eth.gas_price
                            estimated_cost = gas_estimate * gas_price
                            print(f"Estimated cost: {w3.from_wei(estimated_cost, 'ether')} ETH (gasPrice: {w3.from_wei(gas_price, 'gwei')} Gwei)")
                            if balance < estimated_cost:
                                print(f"Insufficient funds: balance={balance_eth} ETH, required={w3.from_wei(estimated_cost, 'ether')} ETH")
                                return jsonify({"error": f"Insufficient funds: {balance_eth} ETH available, {w3.from_wei(estimated_cost, 'ether')} ETH required"}), 500

                            tx = contract.functions.logPullRequest(
                                pr_id, project_name, developer, pr["created_at"], pr_status
                            ).build_transaction({
                                'from': blockchain_account.address,
                                'nonce': nonce,
                                'gas': gas_estimate + 10000,
                                'gasPrice': gas_price,
                                'chainId': 1337
                            })
                            signed_tx = w3.eth.account.sign_transaction(tx, blockchain_account._private_key)
                            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                            if receipt['status'] == 0:
                                pr_data["txHash"] = "Failed"
                                print(f"Transaction failed for PR #{pr_id}: {receipt}")
                                raise Web3Exception(f"Transaction failed: {receipt}")
                            tx_data = w3.eth.get_transaction(tx_hash)
                            decoded_input = contract.decode_function_input(tx_data.input)
                            function_called, function_args = decoded_input
                            print(f"Stored PR #{pr_id} for {project_name} on blockchain, tx: {tx_hash.hex()}, gas used: {receipt['gasUsed']}, attempt: {attempt + 1}")
                            print(f"Transaction receipt: {receipt}")
                            print(f"Function called: {function_called.fn_name}")
                            print(f"Arguments: {function_args}")
                            pr_data["txHash"] = tx_hash.hex()
                            break
                    except Web3Exception as we:
                        print(f"Web3 error for PR #{pr_id} for {project_name} on attempt {attempt + 1}: {str(we)}")
                        pr_data["txHash"] = "Failed"
                        if attempt == max_retries - 1:
                            print(f"Max retries reached for PR #{pr_id}")
                            break
                        time.sleep(1)
                        continue
                    except Exception as e:
                        print(f"Error processing PR #{pr_id} for {project_name} on blockchain on attempt {attempt + 1}: {str(e)}")
                        pr_data["txHash"] = "Failed"
                        if attempt == max_retries - 1:
                            print(f"Max retries reached for PR #{pr_id}")
                            break
                        time.sleep(1)
                        continue

                pullrequests.append(pr_data)
                print(f"Added PR #{pr_id} to response")

        elif response.status_code == 403:
            print(f"Rate limit exceeded for {project_name}: {response.status_code} - {response.text}")
            return jsonify({"error": "GitHub API rate limit exceeded"}), 403
        else:
            print(f"Failed to fetch PRs for {project_name}: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to fetch pull requests: {response.status_code}"}), response.status_code

        points = approved_count - rejected_count
        print(f"Calculated points for project {project_name}: {points} (approved: {approved_count}, rejected: {rejected_count})")
        try:
            db.users.update_one(
                {"_id": ObjectId(user["_id"])},
                {"$set": {f"points.{project_name}": points}}
            )
            print(f"Updated points in MongoDB for project {project_name}: {points}")
        except Exception as e:
            print(f"Failed to update points for project {project_name}: {str(e)}")
            return jsonify({"error": f"Failed to update points: {str(e)}"}), 500

    except Exception as e:
        print(f"Error fetching PRs for {project_name}: {str(e)}")
        return jsonify({"error": f"Error fetching pull requests: {str(e)}"}), 500

    print(f"Returning {len(pullrequests)} pull requests for project {project_name}")
    return jsonify({"pullRequests": pullrequests, "points": points}), 200