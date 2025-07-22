from flask import Flask, jsonify
from flask_cors import CORS

from config.db import connect_db
from routes.auth_routes import auth_bp
from routes.developer_routes import dev_bp
from routes.admin_routes import admin_bp
from routes.webhook_routes import webhook_bp
from routes.auditor_routes import auditor_bp

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
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(dev_bp)                     # '/api/…' paths are inside file
app.register_blueprint(webhook_bp, url_prefix="/api")
app.register_blueprint(auditor_bp, url_prefix="/auditor")

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', debug=True, port=port)
