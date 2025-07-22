def commit_exists(db, commit_hash):
    return db.commits.find_one({"commitHash": commit_hash}) is not None

def save_commit_to_db(db, commit_data):
    db.commits.insert_one(commit_data)

