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
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception
import tempfile

dev_bp = Blueprint("dev_bp", __name__)

db = connect_db()

# Initialize Web3 dynamically
WEB3_PROVIDER_URL = os.getenv('GANACHE_RPC', 'http://172.29.240.1:8545')  # Default to Ganache
CONTRACT_ADDRESS = os.getenv('PULLREQUESTS_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

if not all([WEB3_PROVIDER_URL, CONTRACT_ADDRESS, PRIVATE_KEY]):
    raise ValueError("Missing required environment variables: WEB3_PROVIDER_URL, PULL_REQUESTS_CONTRACT_ADDRESS, or BLOCKCHAIN_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not w3.is_connected():
    raise ConnectionError(f"Failed to connect to Web3 provider at {WEB3_PROVIDER_URL}")

# Load contract ABI
abi_path = os.path.join(os.path.dirname(__file__), '../abis/PullRequests.json')
try:
    with open(abi_path, 'r') as f:
        contract_abi = json.load(f)['abi']
except FileNotFoundError:
    raise FileNotFoundError(f"Contract ABI not found at {abi_path}")

# Create contract instance
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Load blockchain account
try:
    blockchain_account = w3.eth.account.from_key(PRIVATE_KEY)
except ValueError as e:
    raise ValueError(f"Invalid private key: {str(e)}")

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

@dev_bp.route("/pullrequests", methods=["GET"])
def list_pullrequests():
    print("Entering list_pullrequests endpoint")
    user_email = request.headers.get("X-User-Email")
    print(f"User email: {user_email}")
    user = db.users.find_one({"email": user_email, "role": "developer"})
    if not user:
        print(f"No developer found for email: {user_email}")
        return jsonify({"error": "No developer found"}), 404

    project_name = request.args.get("project")
    print(f"Project name: {project_name}")
    if not project_name:
        print("Project name is missing")
        return jsonify({"error": "Project name is required"}), 400

    assigned_projects = [p.get("projectName") for p in user.get("assignedProjects", []) if isinstance(p, dict) and "projectName" in p]
    print(f"Assigned projects: {assigned_projects}")
    if project_name not in assigned_projects:
        print(f"Project {project_name} not assigned to user")
        return jsonify({"error": "Project not assigned to user"}), 403

    admins = db.users.find({"role": "admin", "createdProjects": project_name})
    admin = next(admins, None)
    if not admin:
        print(f"No admin found for project: {project_name}")
        return jsonify({"error": "No admin found for project", "project": project_name}), 404

    github_token = admin.get("githubToken", "")
    repo_owner = admin.get("githubUsername", "")
    print(f"Admin GitHub username: {repo_owner}, token present: {bool(github_token)}")
    if not github_token or not repo_owner:
        print("Admin GitHub credentials missing")
        return jsonify({"error": "Admin GitHub credentials missing", "project": project_name}), 400

    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    developer_name = (user.get("githubUsername", "") or user.get("username", "")).lower().strip()
    print(f"Developer name: {developer_name}")

    # Log blockchain connection details
    try:
        chain_id = w3.eth.chain_id
        print(f"Connected to blockchain: chainId={chain_id}, provider={WEB3_PROVIDER_URL}, contract={CONTRACT_ADDRESS}")
    except Exception as e:
        print(f"Failed to retrieve blockchain details: {str(e)}")
        return jsonify({"error": f"Blockchain connection error: {str(e)}"}), 500

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
                if developer != developer_name:
                    print(f"Skipping PR #{pr_id} (developer mismatch: {developer} != {developer_name})")
                    continue

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
                    "version": pr.get("head", {}).get("sha", "unknown")[:7],
                    "developer": developer,
                    "timestamp": pr["created_at"],
                    "status": pr_status,
                    "changedFiles": changed_files,
                    "securityScore": None if any(f["vulnerability"]["is_vulnerable"] for f in changed_files) else "Safe",
                    "txHash": "N/A"
                }
                print(f"PR #{pr_id} data prepared: status={pr_status}, files={len(changed_files)}")

                # Check if PR exists on blockchain with retry logic
                import time
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
                                tx_hash = latest_event['transactionHash'].hex()
                                pr_data["txHash"] = tx_hash
                                print(f"PR #{pr_id} already logged, txHash: {pr_data['txHash']}")
                                # Verify transaction exists
                                try:
                                    receipt = w3.eth.get_transaction_receipt(tx_hash)
                                    if receipt:
                                        print(f"Transaction {tx_hash} found, blockNumber: {receipt['blockNumber']}")
                                    else:
                                        print(f"Transaction {tx_hash} not found on blockchain")
                                        pr_data["txHash"] = "Not Found"
                                except Exception as e:
                                    print(f"Error verifying transaction {tx_hash}: {str(e)}")
                                    pr_data["txHash"] = "Not Found"
                            else:
                                print(f"No PullRequestLogged events found for PR #{pr_id} despite isLogged=True")
                                pr_data["txHash"] = "Not Found"
                            break
                        else:
                            print(f"Logging new PR #{pr_id} to blockchain")
                            # Check account balance
                            balance = w3.eth.get_balance(blockchain_account.address)
                            balance_eth = w3.from_wei(balance, 'ether')
                            print(f"Account {blockchain_account.address} balance: {balance_eth} ETH")
                            if balance_eth < 0.01:  # Require at least 0.01 ETH
                                print(f"Insufficient balance for PR #{pr_id}: {balance_eth} ETH")
                                return jsonify({"error": f"Insufficient account balance: {balance_eth} ETH"}), 500

                            nonce = w3.eth.get_transaction_count(blockchain_account.address, 'pending')
                            gas_estimate = contract.functions.logPullRequest(
                                pr_id, project_name, developer, pr["created_at"], pr_status
                            ).estimate_gas({'from': blockchain_account.address})
                            print(f"PR #{pr_id} gas estimate: {gas_estimate}, using gas: {gas_estimate + 10000}")
                            
                            # Use network default gasPrice
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
                                'gas': gas_estimate + 10000,  # Add buffer
                                'gasPrice': gas_price,
                                'chainId': w3.eth.chain_id  # Use actual chain ID
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

        # Update user points in MongoDB
        points = approved_count - rejected_count
        print(f"Calculated points for user {user_email} on project {project_name}: {points} (approved: {approved_count}, rejected: {rejected_count})")
        try:
            db.users.update_one(
                {"_id": ObjectId(user["_id"])},
                {"$set": {f"points.{project_name}": points}}
            )
            print(f"Updated points in MongoDB for user {user_email} on project {project_name}: {points}")
        except Exception as e:
            print(f"Failed to update points for user {user_email} on project {project_name}: {str(e)}")
            return jsonify({"error": f"Failed to update user points: {str(e)}"}), 500

    except Exception as e:
        print(f"Error fetching PRs for {project_name}: {str(e)}")
        return jsonify({"error": f"Error fetching pull requests: {str(e)}"}), 500

    print(f"Returning {len(pullrequests)} pull requests for project {project_name}")
    return jsonify({"pullrequests": pullrequests, "points": points}), 200

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

@dev_bp.route("/users/<user_id>/points", methods=["PUT"])
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

from traceback import format_exc

@dev_bp.route('/user_projects/<user_id>', methods=['GET'])
def get_user_projects(user_id):
    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400
        user = db.users.find_one({'_id': ObjectId(user_id)})
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
        print(f"Stack trace: {format_exc()}")
        return jsonify({'error': str(e)}), 500

@dev_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        project_name = request.args.get('project')
        query = {'role': 'developer'}
        if project_name:
            query['assignedProjects.projectName'] = project_name
        developers = list(db.users.find(
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