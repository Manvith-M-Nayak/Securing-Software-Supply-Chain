# from flask import Blueprint, request, jsonify
# from config.db import connect_db
# from config.web3 import get_web3, get_contract
# from models.commit_model import pull_request_exists, save_pull_request_to_db
# from models.user import User
# from eth_account import Account
# import os
# import requests
# from flask import abort

# webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhooks/github")
# db = connect_db()

# w3 = get_web3()
# contract = get_contract(w3)

# PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
# DEPLOYER_ADDRESS = w3.to_checksum_address(os.environ.get("DEPLOYER_ADDRESS"))
# SNYK_API_TOKEN = os.environ.get("SNYK_API_TOKEN")
# SNYK_API_URL = "https://api.snyk.io/v1/deepcode/analyze"

# @webhook_bp.route("/<repo_name>", methods=["POST"])
# def receive_pull_request(repo_name):
#     data = request.get_json()
#     if not data or "action" not in data or data["action"] not in ["opened", "synchronize"] or "pull_request" not in data:
#         return jsonify({"error": "Invalid GitHub webhook payload"}), 400

#     pull_request = data["pull_request"]
#     pull_request_id = str(pull_request["number"])  # GitHub PR number
#     project_name = repo_name  # Use repo_name as project_name
#     version = pull_request.get("head", {}).get("sha", "unknown")[:7]  # Shortened commit SHA as version
#     developer = pull_request["user"]["login"]
#     timestamp = pull_request["created_at"]

#     # Fetch changed files using GitHub API
#     admins = db.users.find({"createdProjects": project_name, "role": "admin"})
#     admin = next(admins, None)
#     if not admin:
#         return jsonify({"error": "No admin found for this repo"}), 404
#     github_token = admin.get("githubToken", "")
#     headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
#     repo_owner = admin.get("githubUsername", "Manvith-M-Nayak")
#     repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pull_request_id}/files"
#     files_response = requests.get(repo_url, headers=headers)
    
#     changed_files = []
#     if files_response.status_code == 200:
#         files_data = files_response.json()
#         changed_files = [{"filename": file["filename"], "content": file.get("patch", "No content available")} for file in files_data]

#     if not all([pull_request_id, project_name, version, developer, timestamp]):
#         return jsonify({"error": "Missing fields"}), 400

#     if pull_request_exists(db, pull_request_id):
#         return jsonify({"message": "Pull request already exists"}), 200

#     pull_request_data = {
#         "pullRequestId": pull_request_id,
#         "projectName": project_name,
#         "version": version,
#         "developer": developer,
#         "timestamp": timestamp,
#         "changedFiles": changed_files,
#         "securityScore": None,
#         "status": "pending"
#     }
#     save_pull_request_to_db(db, pull_request_data)

#     if changed_files:
#         headers = {"Authorization": f"token {SNYK_API_TOKEN}", "Content-Type": "application/json"}
#         payload = {"pullRequestId": pull_request_id, "files": changed_files}
#         response = requests.post(SNYK_API_URL, json=payload, headers=headers)
        
#         if response.status_code == 200:
#             security_score = response.json().get("securityScore", 0)
#             pull_request_data["securityScore"] = security_score
#             save_pull_request_to_db(db, pull_request_data)

#     try:
#         nonce = w3.eth.get_transaction_count(DEPLOYER_ADDRESS)
#         tx = contract.functions.storePullRequest(
#             project_name, version, pull_request_id, developer
#         ).build_transaction({
#             'from': DEPLOYER_ADDRESS,
#             'nonce': nonce,
#             'gas': 3000000,
#             'gasPrice': w3.to_wei('10', 'gwei')
#         })
#         signed_tx = Account.sign_transaction(tx, private_key=PRIVATE_KEY)
#         tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#         tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

#         return jsonify({
#             "message": "Pull request stored successfully",
#             "txHash": tx_hash.hex(),
#             "securityScore": pull_request_data.get("securityScore", "N/A")
#         }), 201

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500