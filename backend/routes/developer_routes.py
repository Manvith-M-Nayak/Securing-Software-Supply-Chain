"""
Developer‑facing API endpoints (NO authentication).

Exposes:
    • POST  /webhook                        ← GitHub calls this
    • GET   /api/commits
    • PATCH /api/commits/<commit_id>/mark-onchain
    • GET   /api/projects
    • PATCH /api/projects/<project_id>/toggle-active
    • GET   /api/project-repos
"""

from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request

from config.db import connect_db

# ─────────────────────────────── Initialization ──────────────────────────────
db = connect_db()
dev_bp = Blueprint("dev_bp", __name__)

# ─────────────────────────── Helper: pretend login ───────────────────────────
def _debug_user():
    """Return one developer so endpoints have a 'current user' in dev mode."""
    user = db.users.find_one({"role": "developer"})
    if user:
        user["_id"] = str(user["_id"])
    return user

# ───────────────────────────── 0. POST /webhook ──────────────────────────────
@dev_bp.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.get_json(silent=True) or {}

    if "zen" in data:  # ping event
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
            continue  # Skip commits with invalid or missing id

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

# ───────────────────────────── 1. GET /api/commits ───────────────────────────
@dev_bp.route("/api/commits", methods=["GET"])
def list_commits():
    user = _debug_user()
    if not user:
        return jsonify({"error": "No developer found"}), 404

    assigned_names = []
    for p in user.get("assignedProjects", []):
        if isinstance(p, dict):
            if "projectName" in p:
                assigned_names.append(p["projectName"])
            elif "name" in p:
                assigned_names.append(p["name"])
        else:
            assigned_names.append(str(p))
    assigned_names = list(dict.fromkeys(assigned_names))

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

    commits = list(
        db.commits
          .find(mongo_filter, {"_id": 0})    # include blockchainTxHash if present
          .sort("timestamp", -1)
    )
    return jsonify(commits), 200

# ──────────────────── 2. PATCH /api/commits/<id>/mark-onchain ───────────────
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
    return jsonify({"message": "Commit flagged on‑chain"}), 200

# ──────────────────────────── 3. GET /api/projects ───────────────────────────
@dev_bp.route("/api/projects", methods=["GET"])
def list_projects():
    user = _debug_user()
    if not user:
        return jsonify({"error": "No developer found"}), 404

    return jsonify(user.get("assignedProjects", [])), 200

# ──────────────── 4. PATCH /api/projects/<id>/toggle-active ──────────────────
@dev_bp.route("/api/projects/<project_id>/toggle-active", methods=["PATCH"])
def toggle_project(project_id):
    user = _debug_user()
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

# ───────────────────── 5. GET /api/project-repos?names=a,b ───────────────────
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
