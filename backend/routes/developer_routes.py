from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request
import subprocess
import json
import requests
import base64
import re
import tempfile
import os
import shutil
from config.db import connect_db

dev_bp = Blueprint("dev_bp", __name__)

db = connect_db()

def check_vulnerabilities(file_content, filename):
    """Run Bearer CLI to scan .py files for vulnerabilities."""
    if not filename.endswith('.py'):
        return {"is_vulnerable": False, "details": "Non-Python file, marked as safe"}

    content_to_scan = file_content
    try:
        if re.match(r'^[A-Za-z0-9+/=]+$', file_content):
            content_to_scan = base64.b64decode(file_content).decode('utf-8', errors='replace')
    except (base64.binascii.Error, UnicodeDecodeError):
        content_to_scan = file_content

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
            return {"is_vulnerable": False, "details": "Bearer scan produced no output"}

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

@dev_bp.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.get_json(silent=True) or {}
    if "zen" in data:
        return jsonify({"message": "Webhook ping received"}), 200

    repo = data.get("repository", {})
    project_name = repo.get("name")
    commits = data.get("commits", [])

    if not project_name or not commits:
        return jsonify({"message": "Nothing to process"}), 200

    stored = []
    skipped = []
    for c in commits:
        commit_id = c.get("id")
        if not commit_id or not isinstance(commit_id, str) or not commit_id.strip():
            skipped.append(c)
            continue

        commit_doc = {
            "id": commit_id,
            "projectName": project_name,
            "message": c.get("message", ""),
            "author": c.get("author", {}).get("name", ""),
            "authorEmail": c.get("author", {}).get("email", ""),
            "timestamp": c.get("timestamp", ""),
            "url": c.get("url", ""),
            "isOnBlockchain": False,
            "createdAt": datetime.utcnow(),
        }

        result = db.commits.update_one(
            {"id": commit_doc["id"]},
            {"$setOnInsert": commit_doc},
            upsert=True,
        )

        if result.upserted_id or result.modified_count == 0:
            stored.append(commit_doc["id"])

    return jsonify({
        "stored": stored,
        "skipped": len(skipped),
        "message": f"{len(stored)} stored, {len(skipped)} skipped"
    }), 201

@dev_bp.route("/api/commits", methods=["GET"])
def list_commits():
    user_email = request.headers.get("X-User-Email")
    user = db.users.find_one({"email": user_email, "role": "developer"})
    if not user:
        return jsonify({"error": "No developer found"}), 404

    assigned_names = [p.get("projectName") for p in user.get("assignedProjects", []) if isinstance(p, dict) and "projectName" in p]
    q_project = request.args.get("project")
    q_author = request.args.get("author") or user.get("githubUsername") or user.get("username")
    q_email = request.args.get("email") or user.get("email")

    mongo_filter = {}
    if q_project:
        mongo_filter["projectName"] = q_project
    elif assigned_names:
        mongo_filter["projectName"] = {"$in": assigned_names}
    if q_author:
        mongo_filter["author"] = q_author
    if q_email:
        mongo_filter["authorEmail"] = {"$regex": q_email, "$options": "i"}

    commits = list(db.commits.find(mongo_filter, {"_id": 0}).sort("timestamp", -1))
    return jsonify(commits), 200

@dev_bp.route("/api/commits/<commit_id>/mark-onchain", methods=["PATCH"])
def mark_commit_onchain(commit_id):
    tx_hash = (request.get_json(silent=True) or {}).get("txHash")
    if not tx_hash:
        return jsonify({"error": "txHash is required"}), 400

    commit = db.commits.find_one({"id": commit_id})
    if not commit:
        return jsonify({"error": "Commit not found"}), 404

    db.commits.update_one(
        {"id": commit_id},
        {
            "$set": {
                "isOnBlockchain": True,
                "blockchainTxHash": tx_hash,
                "onChainAt": commit.get("onChainAt") or datetime.utcnow(),
            }
        },
    )
    return jsonify({"message": "Commit flagged on-chain"}), 200

@dev_bp.route("/api/commits/<commit_id>/store-onchain", methods=["POST"])
def store_commit_onchain(commit_id):
    commit = db.commits.find_one({"id": commit_id})
    if not commit:
        return jsonify({"error": "Commit not found"}), 404

    if commit.get("isOnBlockchain") and commit.get("blockchainTxHash"):
        return jsonify({"message": "Commit already stored on chain"}), 200

    try:
        cmd = [
            "node",
            "blockchain/store_commit.js",
            json.dumps({
                "projectName": commit["projectName"],
                "commitId": commit["id"],
                "message": commit["message"],
                "authorEmail": commit["authorEmail"],
                "timestamp": commit["timestamp"]
            })
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        output = json.loads(result.stdout)
        tx_hash = output.get("transactionHash")
        if not tx_hash:
            return jsonify({"error": "No transaction hash returned"}), 500

        db.commits.update_one(
            {"id": commit_id},
            {
                "$set": {
                    "isOnBlockchain": True,
                    "blockchainTxHash": tx_hash,
                    "onChainAt": datetime.utcnow(),
                }
            },
        )
        return jsonify({"message": "Commit stored on-chain", "txHash": tx_hash}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dev_bp.route("/api/projects", methods=["GET"])
def list_projects():
    user_email = request.headers.get("X-User-Email")
    user = db.users.find_one({"email": user_email, "role": "developer"})
    if not user:
        return jsonify({"error": "No developer found"}), 404
    return jsonify(user.get("assignedProjects", [])), 200

@dev_bp.route("/api/projects/<id>/toggle-active", methods=["PATCH"])
def toggle_project(project_id):
    user_email = request.headers.get("X-User-Email")
    user = db.users.find_one({"email": user_email, "role": "developer"})
    if not user:
        return jsonify({"error": "No developer found"}), 404

    updated = None
    for proj in user.get("assignedProjects", []):
        key = str(proj.get("_id") or proj.get("id") or proj.get("projectName") or proj.get("name"))
        if key == project_id:
            proj["isActive"] = not proj.get("isActive", False)
            updated = proj
            break

    if updated is None:
        return jsonify({"error": "Project not found"}), 404

    db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"assignedProjects": user["assignedProjects"]}},
    )
    return jsonify(updated), 200

@dev_bp.route("/api/project-repos", methods=["GET"])
def project_repos():
    names_raw = request.args.get("names", "")
    wanted = [n.strip() for n in names_raw.split(",") if n.strip()]
    result = {}
    if not wanted:
        return jsonify(result), 200

    cursor = db.users.find(
        {"createdProjects": {"$in": wanted}},
        {"githubUsername": 1, "createdProjects": 1, "projectRepos": 1},
    )
    for user in cursor:
        owner = user.get("githubUsername", "")
        for proj in user.get("createdProjects", []):
            if proj in wanted:
                explicit = user.get("projectRepos", {}).get(proj) if "projectRepos" in user else None
                result[proj] = explicit or f"https://github.com/{owner}/{proj}"
    return jsonify(result), 200

@dev_bp.route("/api/pullrequests", methods=["GET"])
def list_pullrequests():
    user_email = request.headers.get("X-User-Email")
    user = db.users.find_one({"email": user_email, "role": "developer"})
    if not user:
        return jsonify({"error": "No developer found"}), 404

    project_name = request.args.get("project")
    if not project_name:
        return jsonify({"error": "Project name is required"}), 400

    assigned_projects = [p.get("projectName") for p in user.get("assignedProjects", []) if isinstance(p, dict) and "projectName" in p]
    if project_name not in assigned_projects:
        return jsonify({"error": "Project not assigned to user"}), 403

    admins = db.users.find({"role": "admin", "createdProjects": project_name})
    admin = next(admins, None)
    if not admin:
        return jsonify({"error": "No admin found for project", "project": project_name}), 404

    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "")
    if not github_token or not repo_owner:
        return jsonify({"error": "Admin GitHub credentials missing", "project": project_name}), 400

    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    developer_name = (user.get("githubUsername", "") or user.get("username", "")).lower().strip()

    pullrequests = []
    try:
        repo_check_url = f"https://api.github.com/repos/{repo_owner}/{project_name}"
        repo_response = requests.get(repo_check_url, headers=headers)
        if repo_response.status_code == 404:
            print(f"Repository not found: {project_name}")
            return jsonify({"error": f"Repository {project_name} not found"}), 404
        elif repo_response.status_code == 403:
            print(f"Rate limit exceeded checking repository {project_name}: {repo_response.status_code} - {repo_response.text}")
            return jsonify({"error": "GitHub API rate limit exceeded"}), 403

        repo_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls?state=all"
        response = requests.get(repo_url, headers=headers)
        print(f"GitHub API response for {project_name}: status={response.status_code}, data={response.text[:200]}...")

        if response.status_code == 200:
            prs = response.json()
            for pr in prs:
                pr_id = str(pr["number"])
                developer = (pr["user"]["login"] or "").lower().strip()
                if developer != developer_name:
                    continue

                files_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pr_id}/files"
                files_response = requests.get(files_url, headers=headers)
                changed_files = []

                if files_response.status_code == 200:
                    files_data = files_response.json()
                    for file in files_data:
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

                        vuln_result = check_vulnerabilities(file_content, file["filename"])
                        changed_files.append({
                            "filename": file["filename"],
                            "content": file_content,
                            "vulnerability": vuln_result
                        })

                pullrequests.append({
                    "pullRequestId": pr_id,
                    "projectName": project_name,
                    "version": pr.get("head", {}).get("sha", "unknown")[:7],
                    "developer": developer,
                    "timestamp": pr["created_at"],
                    "status": "approved" if pr.get("merged_at") else ("rejected" if pr["state"] == "closed" else "pending"),
                    "changedFiles": changed_files,
                    "securityScore": None if any(f["vulnerability"]["is_vulnerable"] for f in changed_files) else "Safe"
                })

        elif response.status_code == 403:
            print(f"Rate limit exceeded for {project_name}: {response.status_code} - {response.text}")
            return jsonify({"error": "GitHub API rate limit exceeded"}), 403
        else:
            print(f"Failed to fetch PRs for {project_name}: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to fetch pull requests: {response.status_code}"}), response.status_code

    except Exception as e:
        print(f"Error fetching PRs for {project_name}: {str(e)}")
        return jsonify({"error": f"Error fetching pull requests: {str(e)}"}), 500

    return jsonify({"pullrequests": pullrequests}), 200

@dev_bp.route("/api/users/<user_id>/points", methods=["PUT"])
def update_user_points(user_id):
    data = request.get_json(silent=True) or {}
    points = data.get("points")
    project_name = data.get("projectName")

    if points is None or not isinstance(points, int):
        print(f"Invalid points value: {points}")
        return jsonify({"error": "Invalid or missing points value"}), 400

    if not project_name:
        print("Missing projectName")
        return jsonify({"error": "Project name is required"}), 400

    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({"error": "Invalid user ID format"}), 400

        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {f"points.{project_name}": points}}
        )

        if result.matched_count == 0:
            print(f"No user found for ID: {user_id}")
            return jsonify({"error": "User not found"}), 404

        print(f"Updated points for user {user_id}, project {project_name}: {points}")
        return jsonify({"message": f"User points updated for {project_name}", "points": points}), 200
    except Exception as e:
        print(f"Failed to update user points for user {user_id}, project {project_name}: {str(e)}")
        return jsonify({"error": f"Failed to update user points: {str(e)}"}), 500