from flask import Blueprint, request, jsonify
from config.db import connect_db

# Connect to MongoDB
db = connect_db()
version_routes = Blueprint('version_routes', __name__)
version_collection = db['version_submissions']

@version_routes.route('/submit', methods=['POST'])
def save_version_to_mongo():
    """
    This route receives version submissions from the frontend,
    validates the data, and stores it in the MongoDB collection
    called 'version_submissions'.
    """

    try:
        data = request.get_json()

        # Define required fields
        required_fields = [
            'username',
            'componentId',
            'version',
            'commitHash',
            'hash',         # Blockchain transaction hash
            'timestamp'
        ]

        # Validate all required fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Prepare record
        record = {
            'username': data['username'],
            'componentId': data['componentId'],
            'version': data['version'],
            'commitHash': data['commitHash'],
            'blockchainHash': data['hash'],
            'timestamp': data['timestamp']
        }

        # Insert into MongoDB
        version_collection.insert_one(record)

        return jsonify({'message': 'Version data saved successfully in MongoDB'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@version_routes.route('/all', methods=['GET'])
def get_all_versions():
    """
    Optional: Retrieve all version submissions for debugging or admin inspection.
    """
    try:
        versions = list(version_collection.find({}, {'_id': 0}))
        return jsonify({'versions': versions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
