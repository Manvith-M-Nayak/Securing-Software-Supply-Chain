from flask import Blueprint, request, jsonify
from config.db import connect_db
from models.user import User
from models.commit_model import get_pull_requests_by_project, pull_request_exists, save_pull_request_to_db
import requests

auditor_bp = Blueprint("auditor", __name__, url_prefix="/auditor")
db = connect_db()

@auditor_bp.route("/dashboard", methods=["GET"])
def auditor_dashboard():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        return jsonify({"error": "Unauthorized"}), 403

    project_name = request.args.get("projectName")
    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    
    if project_name not in assigned_projects:
        return jsonify({"error": "Unauthorized project"}), 403

    # Determine repo owner from admin
    admins = db.users.find({"createdProjects": project_name, "role": "admin"})
    admin = next(admins, None)
    if not admin:
        return jsonify({"error": "No admin found for this repo"}), 404
    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    repo_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls?state=all"
    response = requests.get(repo_url, headers=headers)
    
    pull_requests = []
    if response.status_code == 200:
        pull_requests = response.json()
        for pr in pull_requests:
            pr_id = str(pr["number"])
            if not pull_request_exists(db, pr_id):
                version = pr.get("head", {}).get("sha", "unknown")[:7]
                developer = pr["user"]["login"]
                timestamp = pr["created_at"]
                files_url = f"https://api.github.com/repos/{repo_owner}/{project_name}/pulls/{pr_id}/files"
                files_response = requests.get(files_url, headers=headers)
                changed_files = []
                if files_response.status_code == 200:
                    files_data = files_response.json()
                    changed_files = [{"filename": file["filename"], "content": file.get("patch", "No content available")} for file in files_data]
                pull_request_data = {
                    "pullRequestId": pr_id,
                    "projectName": project_name,
                    "version": version,
                    "developer": developer,
                    "timestamp": timestamp,
                    "changedFiles": changed_files,
                    "securityScore": None,
                    "status": "pending"
                }
                save_pull_request_to_db(db, pull_request_data)

    db_pull_requests = get_pull_requests_by_project(db, project_name)
    pending_pull_requests = [pr for pr in db_pull_requests if pr.get("status") == "pending"]
    
    return jsonify({
        "pullRequests": [{
            "pullRequestId": pr["pullRequestId"],
            "projectName": pr["projectName"],
            "version": pr["version"],
            "developer": pr["developer"],
            "timestamp": pr["timestamp"],
            "changedFiles": pr["changedFiles"],
            "securityScore": pr["securityScore"],
            "status": pr["status"]
        } for pr in pending_pull_requests]
    }), 200

@auditor_bp.route("/decision", methods=["POST"])
def auditor_decision():
    user_email = request.headers.get("X-User-Email")
    user = User.find_by_email(db, user_email)
    
    if not user or user.get("role") != "auditor":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    pull_request_id = data.get("pullRequestId")
    decision = data.get("decision")

    pull_request = db.pull_requests.find_one({"pullRequestId": pull_request_id})
    if not pull_request:
        return jsonify({"error": "Pull request not found"}), 404

    assigned_projects = [p["projectName"] for p in user.get("assignedProjects", [])]
    if pull_request.get("projectName") not in assigned_projects:
        return jsonify({"error": "Unauthorized project"}), 403

    # Determine repo owner from admin
    admins = db.users.find({"createdProjects": pull_request["projectName"], "role": "admin"})
    admin = next(admins, None)
    if not admin:
        return jsonify({"error": "No admin found for this repo"}), 404
    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    if decision == "approve":
        # Submit an approving review
        review_url = f"https://api.github.com/repos/{repo_owner}/{pull_request['projectName']}/pulls/{pull_request_id}/reviews"
        review_payload = {
            "event": "APPROVE",
            "body": "Approved by auditor"
        }
        review_response = requests.post(review_url, headers=headers, json=review_payload)
        if review_response.status_code != 200 and review_response.status_code != 201:
            return jsonify({"error": f"Failed to submit review: {review_response.text}"}), 500

        # Merge the pull request into the main branch
        merge_url = f"https://api.github.com/repos/{repo_owner}/{pull_request['projectName']}/pulls/{pull_request_id}/merge"
        merge_response = requests.put(merge_url, headers=headers, json={"merge_method": "merge"})
        if merge_response.status_code == 200:
            pull_request["status"] = "approved"
            db.pull_requests.update_one({"pullRequestId": pull_request_id}, {"$set": pull_request})
            return jsonify({"message": "Pull request approved and merged"}), 200
        else:
            return jsonify({"error": f"Failed to merge pull request: {merge_response.text}"}), 500
    elif decision == "reject":
        # Close the pull request
        close_url = f"https://api.github.com/repos/{repo_owner}/{pull_request['projectName']}/pulls/{pull_request_id}"
        close_response = requests.patch(close_url, headers=headers, json={"state": "closed"})
        if close_response.status_code == 200:
            pull_request["status"] = "rejected"
            db.pull_requests.update_one({"pullRequestId": pull_request_id}, {"$set": pull_request})
            return jsonify({"message": "Pull request rejected and closed"}), 200
        else:
            return jsonify({"error": f"Failed to close pull request: {close_response.text}"}), 500
    else:
        return jsonify({"error": "Invalid decision"}), 400