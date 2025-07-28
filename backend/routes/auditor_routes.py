from flask import Blueprint, request, jsonify
from config.db import connect_db
from models.user import User
import requests
import re
import base64
import subprocess
import tempfile
import os
import json
import shutil

auditor_bp = Blueprint("auditor", __name__, url_prefix="/auditor")
db = connect_db()

def check_vulnerabilities(file_content, filename):
    """Run Bearer CLI to scan .py files for vulnerabilities."""
    print(f"Starting vulnerability scan for {filename}")
    
    if not filename.endswith('.py'):
        print(f"Skipping scan for {filename}: Non-Python file")
        return {"is_vulnerable": False, "details": "Non-Python file, marked as safe"}

    # Validate file content
    if not file_content or file_content.strip() == "":
        print(f"No content provided for {filename}")
        return {"is_vulnerable": False, "details": "Empty file content"}

    # Try to decode as base64, fallback to raw content
    content_to_scan = file_content
    try:
        if re.match(r'^[A-Za-z0-9+/=]+$', file_content):
            content_to_scan = base64.b64decode(file_content).decode('utf-8', errors='replace')
            print(f"Successfully decoded base64 content for {filename}")
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        print(f"Base64 decode failed for {filename}: {str(e)}. Using raw content.")
        content_to_scan = file_content

    # Check for Bearer CLI availability
    bearer_path = shutil.which('bearer')
    if not bearer_path:
        print("Bearer CLI not found in PATH. Attempting default location: /usr/local/bin/bearer")
        bearer_path = '/usr/local/bin/bearer'
    
    if not os.path.exists(bearer_path):
        print(f"Bearer CLI not found at {bearer_path}. Ensure Bearer is installed.")
        return {"is_vulnerable": False, "details": f"Bearer CLI not installed at {bearer_path}"}

    # Verify Bearer CLI version
    try:
        version_result = subprocess.run(
            [bearer_path, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Bearer CLI version: {version_result.stdout.strip()}")
    except Exception as e:
        print(f"Failed to verify Bearer CLI version: {str(e)}")
        return {"is_vulnerable": False, "details": f"Failed to verify Bearer CLI: {str(e)}"}

    vulnerabilities = []
    temp_file_path = None
    stderr_file_path = None
    try:
        # Create temporary file for scanning
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(content_to_scan)
            temp_file_path = temp_file.name
        print(f"Created temporary file for scan: {temp_file_path}")

        # Create temporary file for stderr
        stderr_fd, stderr_file_path = tempfile.mkstemp(suffix='.txt')
        os.close(stderr_fd)
        print(f"Created stderr file: {stderr_file_path}")

        # Run Bearer CLI scan
        print(f"Executing Bearer scan: {bearer_path} scan {temp_file_path} --format json --quiet")
        result = subprocess.run(
            [bearer_path, 'scan', temp_file_path, '--format', 'json', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Read stderr
        stderr_output = ""
        try:
            with open(stderr_file_path, 'r', encoding='utf-8') as stderr_file:
                stderr_output = stderr_file.read()
        except Exception as e:
            print(f"Failed to read stderr file {stderr_file_path}: {str(e)}")

        # Log scan results
        print(f"Bearer scan stdout for {filename}: {result.stdout}")
        print(f"Bearer scan stderr for {filename}: {stderr_output}")
        print(f"Bearer scan return code for {filename}: {result.returncode}")

        # Parse Bearer output
        if result.stdout:
            try:
                bearer_output = json.loads(result.stdout)
                for severity in ['critical', 'high', 'medium', 'low', 'warning']:
                    for finding in bearer_output.get(severity, []):
                        vulnerabilities.append({
                            "type": finding.get('title', 'Unknown Vulnerability'),
                            "line": finding.get('line_number', 1),
                            "snippet": finding.get('code_extract', finding.get('snippet', 'No snippet available'))
                        })
                if vulnerabilities:
                    print(f"Vulnerabilities found in {filename}: {vulnerabilities}")
                else:
                    print(f"No vulnerabilities detected in {filename}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse Bearer JSON output for {filename}: {str(e)}")
                return {"is_vulnerable": False, "details": f"Failed to parse Bearer output: {str(e)}"}
        else:
            print(f"Bearer scan produced no output for {filename}")
            return {"is_vulnerable": False, "details": "Bearer scan produced no output"}

        if stderr_output:
            print(f"Bearer scan error output for {filename}: {stderr_output}")
            return {"is_vulnerable": False, "details": f"Bearer scan failed: {stderr_output}"}

    except subprocess.TimeoutExpired:
        print(f"Bearer scan timed out for {filename}")
        return {"is_vulnerable": False, "details": "Bearer scan timed out"}
    except subprocess.SubprocessError as e:
        print(f"Subprocess error during Bearer scan for {filename}: {str(e)}")
        return {"is_vulnerable": False, "details": f"Subprocess error: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error during Bearer scan for {filename}: {str(e)}")
        return {"is_vulnerable": False, "details": f"Failed to scan file: {str(e)}"}
    finally:
        # Clean up temporary files
        for path in [temp_file_path, stderr_file_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    print(f"Cleaned up temporary file: {path}")
                except Exception as e:
                    print(f"Failed to delete temporary file {path}: {str(e)}")

    return {
        "is_vulnerable": bool(vulnerabilities),
        "details": vulnerabilities if vulnerabilities else "No vulnerabilities detected"
    }

@auditor_bp.route("/dashboard", methods=["GET"])
def auditor_dashboard():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        print(f"Unauthorized access attempt by {user_email}")
        return jsonify({"error": "Unauthorized"}), 403

    project_name = request.args.get("projectName")
    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    
    if not project_name or project_name not in assigned_projects:
        print(f"Invalid project {project_name} for user {user_email}. Assigned projects: {assigned_projects}")
        return jsonify({"error": "Unauthorized project or no project specified"}), 403

    # Find admin for the project
    admins = db.users.find({"createdProjects": project_name, "role": "admin"})
    admin = next(admins, None)
    if not admin:
        print(f"No admin found for project {project_name}")
        return jsonify({"error": "No admin found for this repo"}), 404
    
    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    
    # Fetch pull requests from GitHub
    repo_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls?state=open"
    print(f"Fetching pull requests from {repo_url}")
    response = requests.get(repo_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch pull requests: {response.text}")
        return jsonify({"error": f"Failed to fetch pull requests: {response.text}"}), response.status_code

    pull_requests = []
    for pr in response.json():
        pr_id = str(pr["number"])
        files_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pr_id}/files"
        print(f"Fetching files for PR {pr_id}")
        files_response = requests.get(files_url, headers=headers)
        
        changed_files = []
        if files_response.status_code == 200:
            files_data = files_response.json()
            for file in files_data:
                # Prefer raw file content from contents_url
                file_content = None
                if "contents_url" in file:
                    print(f"Fetching content from {file['contents_url']}")
                    content_response = requests.get(file["contents_url"], headers=headers)
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        if "content" in content_data and content_data.get("encoding") == "base64":
                            try:
                                file_content = base64.b64decode(content_data["content"]).decode('utf-8', errors='replace')
                                print(f"Successfully fetched content for {file['filename']}")
                            except (base64.binascii.Error, UnicodeDecodeError) as e:
                                print(f"Failed to decode content for {file['filename']}: {str(e)}")
                                file_content = file.get("patch", "No content available")
                if not file_content:
                    print(f"No content from contents_url for {file['filename']}, using patch")
                    file_content = file.get("patch", "No content available")
                
                # Run vulnerability scan
                vuln_result = check_vulnerabilities(file_content, file["filename"])
                
                changed_files.append({
                    "filename": file["filename"],
                    "content": file_content,
                    "vulnerability": vuln_result
                })
        
        pull_requests.append({
            "pullRequestId": pr_id,
            "projectName": project_name,
            "version": pr.get("head", {}).get("sha", "unknown")[:7],
            "developer": pr["user"]["login"],
            "timestamp": pr["created_at"],
            "changedFiles": changed_files,
            "securityScore": None if any(f["vulnerability"]["is_vulnerable"] for f in changed_files) else "Safe",
            "status": "pending"
        })

    print(f"Returning {len(pull_requests)} pull requests for project {project_name}")
    return jsonify({"pullRequests": pull_requests}), 200

@auditor_bp.route("/decision", methods=["POST"])
def auditor_decision():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        print(f"Unauthorized decision attempt by {user_email}")
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    pull_request_id = data.get("pullRequestId")
    decision = data.get("decision")
    project_name = data.get("projectName")

    if not project_name or not pull_request_id or not decision:
        print(f"Missing fields in decision request: {data}")
        return jsonify({"error": "Missing required fields"}), 400

    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    if project_name not in assigned_projects:
        print(f"Unauthorized project {project_name} for user {user_email}")
        return jsonify({"error": "Unauthorized project"}), 403

    # Find admin for the project
    admins = db.users.find({"createdProjects": project_name, "role": "admin"})
    admin = next(admins, None)
    if not admin:
        print(f"No admin found for project {project_name}")
        return jsonify({"error": "No admin found for this repo"}), 404
    
    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    if decision == "approve":
        review_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pull_request_id}/reviews"
        review_payload = {
            "event": "APPROVE",
            "body": "Approved by auditor"
        }
        print(f"Submitting approval for PR {pull_request_id}")
        review_response = requests.post(review_url, headers=headers, json=review_payload)
        if review_response.status_code not in (200, 201):
            print(f"Failed to submit review for PR {pull_request_id}: {review_response.text}")
            return jsonify({"error": f"Failed to submit review: {review_response.text}"}), 500

        merge_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pull_request_id}/merge"
        print(f"Merging PR {pull_request_id}")
        merge_response = requests.put(merge_url, headers=headers, json={"merge_method": "merge"})
        if merge_response.status_code == 200:
            print(f"PR {pull_request_id} approved and merged")
            return jsonify({"message": "Pull request approved and merged"}), 200
        else:
            print(f"Failed to merge PR {pull_request_id}: {merge_response.text}")
            return jsonify({"error": f"Failed to merge pull request: {merge_response.text}"}), 500
    elif decision == "reject":
        close_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pull_request_id}"
        print(f"Closing PR {pull_request_id}")
        close_response = requests.patch(close_url, headers=headers, json={"state": "closed"})
        if close_response.status_code == 200:
            print(f"PR {pull_request_id} rejected and closed")
            return jsonify({"message": "Pull request rejected and closed"}), 200
        else:
            print(f"Failed to close PR {pull_request_id}: {close_response.text}")
            return jsonify({"error": f"Failed to close pull request: {close_response.text}"}), 500
    else:
        print(f"Invalid decision {decision} for PR {pull_request_id}")
        return jsonify({"error": "Invalid decision"}), 400