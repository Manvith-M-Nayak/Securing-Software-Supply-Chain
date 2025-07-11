from flask import Flask, jsonify
from flask_cors import CORS
from config.db import connect_db
from routes.auth_routes import auth_bp
from routes.version_routes import version_routes
from routes.admin_routes import admin_bp  # ✅ this will now work
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Connect to MongoDB
db = connect_db()

# Root endpoint
@app.route('/')
def home():
    return jsonify({"message": "API is running"}), 200

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(version_routes, url_prefix='/api/versions')
app.register_blueprint(admin_bp, url_prefix='/admin')  

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', debug=True, port=port)
