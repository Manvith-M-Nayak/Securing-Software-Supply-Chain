from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
import bcrypt
from config.db import connect_db

db = connect_db()
users_col = db['users']
auth_bp = Blueprint('auth', __name__)

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

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    required = ['username', 'email', 'password', 'role', 'githubUsername', 'githubToken']
    if not all(data.get(x) for x in required):
        return jsonify({'error': 'All fields required'}), 400
    if users_col.find_one({'$or': [{'username': data['username']}, {'email': data['email'].lower()}]}):
        return jsonify({'error': 'User exists'}), 409
    user = {
        'username': data['username'],
        'email': data['email'].lower(),
        'password': bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt()),
        'role': data['role'],
        'githubUsername': data['githubUsername'],
        'githubToken': data['githubToken']
    }
    if data['role'] == 'admin':
        user['createdProjects'] = data.get('createdProjects', [])
    else:
        user['assignedProjects'] = data.get('assignedProjects', [])
        if data['role'] == 'developer':
            user['points'] = {}  # Initialize points as an empty object for developers
    res = users_col.insert_one(user)
    user['_id'] = res.inserted_id
    print(f"Registered user: {user['username']}")
    return jsonify({'user': serialize_user(user, mask=False)}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    body = request.get_json() or {}
    identifier = body.get('username') or body.get('email')
    pw = body.get('password', '')
    if not identifier or not pw:
        return jsonify({'error': 'Credentials required'}), 400
    user = users_col.find_one({'$or': [{'username': identifier}, {'email': identifier.lower()}]})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if not bcrypt.checkpw(pw.encode(), user['password']):
        print(f"Login failed for identifier: {identifier}")
        return jsonify({'error': 'Invalid credentials'}), 401
    print(f"Login successful for user: {user['username']}")
    return jsonify({'user': serialize_user(user, mask=False)}), 200

@auth_bp.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json() or {}
    points = data.get('points')
    project_name = data.get('projectName')
    
    if points is None or not isinstance(points, int):
        print(f"Invalid points value: {points}")
        return jsonify({'error': 'Invalid or missing points value'}), 400
    if not project_name or not isinstance(project_name, str) or not project_name.strip():
        print(f"Invalid projectName: {project_name}")
        return jsonify({'error': 'Invalid or missing project name'}), 400

    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400

        user = users_col.find_one({'_id': ObjectId(user_id), 'role': 'developer'})
        if not user:
            print(f"No developer found for ID: {user_id}")
            return jsonify({'error': 'Developer not found'}), 404
        if isinstance(user.get('points'), list):
            print(f"Invalid points field type for user {user_id}: expected object, got array")
            return jsonify({'error': 'User points field must be an object, not an array'}), 400

        result = users_col.update_one(
            {'_id': ObjectId(user_id), 'role': 'developer'},
            {'$set': {f'points.{project_name}': points}}
        )
        if result.matched_count == 0:
            print(f"No developer found for ID: {user_id}")
            return jsonify({'error': 'Developer not found'}), 404
        print(f"Updated points for user {user_id}, project {project_name}: {points}")
        return jsonify({'message': f'Points updated for {project_name}', 'points': points}), 200
    except Exception as e:
        print(f"Failed to update user points for user {user_id}, project {project_name}: {str(e)}")
        return jsonify({'error': f'Failed to update user points: {str(e)}'}), 500

@auth_bp.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        if not ObjectId.is_valid(user_id):
            print(f"Invalid user_id: {user_id}")
            return jsonify({'error': 'Invalid user ID format'}), 400
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            print(f"No user found for ID: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        print(f"Retrieved user: {user['username']}")
        return jsonify({'user': serialize_user(user, mask=False)}), 200
    except Exception as e:
        print(f"Failed to retrieve user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500