from config.db import connect_db

db = connect_db()

def pull_request_exists(db, pull_request_id):
    return db.pull_requests.find_one({"pullRequestId": pull_request_id}) is not None

def save_pull_request_to_db(db, pull_request_data):
    db.pull_requests.update_one(
        {"pullRequestId": pull_request_data["pullRequestId"]},
        {"$set": pull_request_data},
        upsert=True
    )

def get_pull_requests_by_project(db, project_name):
    return list(db.pull_requests.find({"projectName": project_name}))