# Project model for MongoDB

def project_doc(name, admin_id, collaborators=None, invite_tokens=None):
    return {
        "name": name,
        "adminId": admin_id,
        "collaborators": collaborators or [],
        "inviteTokens": invite_tokens or [],
        "createdAt": None,
    } 