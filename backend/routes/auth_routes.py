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
        'githubUsername': doc.get('githubUsername', '')
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
    res = users_col.insert_one(user)
    user['_id'] = res.inserted_id
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
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify({'user': serialize_user(user, mask=False)}), 200
