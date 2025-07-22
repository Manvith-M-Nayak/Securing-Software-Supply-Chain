# User model for MongoDB

def user_doc(username, email, password, role, github_username, github_token, assigned_projects=None, created_projects=None):
    doc = {
        "username": username,
        "email": email,
        "password": password,
        "role": role,  # developer, admin, auditor
        "githubUsername": github_username,
        "githubToken": github_token,
    }
    if role == "admin":
        doc["createdProjects"] = created_projects or []
    else:
        doc["assignedProjects"] = assigned_projects or []
    return doc 