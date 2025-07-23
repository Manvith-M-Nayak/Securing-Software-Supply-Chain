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
    if not filename.endswith('.py'):
        return {"is_vulnerable": False, "details": "Non-Python file, marked as safe"}
    
    # Try to decode as base64, but fallback to raw content if it fails
    content_to_scan = file_content
    try:
        if re.match(r'^[A-Za-z0-9+/=]+$', file_content):
            content_to_scan = base64.b64decode(file_content).decode('utf-8', errors='replace')
    except (base64.binascii.Error, UnicodeDecodeError):
        content_to_scan = file_content

    # Ensure Bearer CLI is available
    bearer_path = shutil.which('bearer') or '/usr/local/bin/bearer'
    if not os.path.exists(bearer_path):
        print(f"Bearer CLI not found at {bearer_path}")
        return {"is_vulnerable": False, "details": "Bearer CLI not installed or not found"}

    # Create a temporary file for Bearer scanning
    vulnerabilities = []
    temp_file_path = None
    stderr_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(content_to_scan)
            temp_file_path = temp_file.name
        
        # Create a temporary file for stderr
        stderr_fd, stderr_file_path = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(stderr_fd, 'w') as stderr_file:
            stderr_file.write("")  # Initialize empty file
        
        # Run Bearer CLI scan
        result = subprocess.run(
            [bearer_path, 'scan', temp_file_path, '--format', 'json', '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Read stderr from file
        with open(stderr_file_path, 'r', encoding='utf-8') as stderr_file:
            stderr_output = stderr_file.read()
        
        # Log raw output for debugging
        print(f"Bearer scan stdout for {filename}: {result.stdout}")
        print(f"Bearer scan stderr for {filename}: {stderr_output}")
        print(f"Bearer scan return code for {filename}: {result.returncode}")
        
        # Parse Bearer output, even if return code is non-zero (Bearer returns 1 for vulnerabilities)
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
            except json.JSONDecodeError as e:
                print(f"Failed to parse Bearer JSON output for {filename}: {str(e)}")
                return {"is_vulnerable": False, "details": f"Failed to parse Bearer output: {str(e)}"}
        
        # If no vulnerabilities and stderr indicates an error, return failure
        if not vulnerabilities and stderr_output:
            print(f"Bearer scan error for {filename}: {stderr_output}")
            return {"is_vulnerable": False, "details": f"Bearer scan failed: {stderr_output}"}
        elif not vulnerabilities and not result.stdout:
            print(f"Bearer scan produced no output for {filename}")
            return {"is_vulnerable": False, "details": "Bearer scan produced no output"}
        
    except subprocess.TimeoutExpired:
        print(f"Bearer scan timed out for {filename}")
        return {"is_vulnerable": False, "details": "Bearer scan timed out"}
    except Exception as e:
        print(f"Error running Bearer scan for {filename}: {str(e)}")
        return {"is_vulnerable": False, "details": f"Failed to scan file: {str(e)}"}
    finally:
        # Clean up temporary files
        for path in [temp_file_path, stderr_file_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    print(f"Failed to delete temporary file {path}: {str(e)}")
    
    if vulnerabilities:
        return {"is_vulnerable": True, "details": vulnerabilities}
    return {"is_vulnerable": False, "details": "No vulnerabilities detected"}

@auditor_bp.route("/dashboard", methods=["GET"])
def auditor_dashboard():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        return jsonify({"error": "Unauthorized"}), 403

    project_name = request.args.get("projectName")
    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    
    if not project_name or project_name not in assigned_projects:
        return jsonify({"error": "Unauthorized project or no project specified"}), 403

    # Find admin for the project
    admins = db.users.find({"createdProjects": project_name, "role": "admin"})
    admin = next(admins, None)
    if not admin:
        return jsonify({"error": "No admin found for this repo"}), 404
    
    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    
    # Fetch pull requests from GitHub
    repo_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls?state=open"
    response = requests.get(repo_url, headers=headers)
    
    if response.status_code != 200:
        return jsonify({"error": f"Failed to fetch pull requests: {response.text}"}), response.status_code

    pull_requests = []
    for pr in response.json():
        pr_id = str(pr["number"])
        files_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pr_id}/files"
        files_response = requests.get(files_url, headers=headers)
        
        changed_files = []
        if files_response.status_code == 200:
            files_data = files_response.json()
            for file in files_data:
                # Prefer raw file content from contents_url
                file_content = None
                if "contents_url" in file:
                    content_response = requests.get(file["contents_url"], headers=headers)
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        if "content" in content_data and content_data.get("encoding") == "base64":
                            try:
                                file_content = base64.b64decode(content_data["content"]).decode('utf-8', errors='replace')
                            except (base64.binascii.Error, UnicodeDecodeError):
                                file_content = file.get("patch", "No content available")
                if not file_content:
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

    return jsonify({"pullRequests": pull_requests}), 200

@auditor_bp.route("/decision", methods=["POST"])
def auditor_decision():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    pull_request_id = data.get("pullRequestId")
    decision = data.get("decision")
    project_name = data.get("projectName")

    if not project_name or not pull_request_id or not decision:
        return jsonify({"error": "Missing required fields"}), 400

    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    if project_name not in assigned_projects:
        return jsonify({"error": "Unauthorized project"}), 403

    # Find admin for the project
    admins = db.users.find({"createdProjects": project_name, "role": "admin"})
    admin = next(admins, None)
    if not admin:
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
        review_response = requests.post(review_url, headers=headers, json=review_payload)
        if review_response.status_code not in (200, 201):
            return jsonify({"error": f"Failed to submit review: {review_response.text}"}), 500

        merge_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pull_request_id}/merge"
        merge_response = requests.put(merge_url, headers=headers, json={"merge_method": "merge"})
        if merge_response.status_code == 200:
            return jsonify({"message": "Pull request approved and merged"}), 200
        else:
            return jsonify({"error": f"Failed to merge pull request: {merge_response.text}"}), 500
    elif decision == "reject":
        close_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pull_request_id}"
        close_response = requests.patch(close_url, headers=headers, json={"state": "closed"})
        if close_response.status_code == 200:
            return jsonify({"message": "Pull request rejected and closed"}), 200
        else:
            return jsonify({"error": f"Failed to close pull request: {close_response.text}"}), 500
    else:
        return jsonify({"error": "Invalid decision"}), 400