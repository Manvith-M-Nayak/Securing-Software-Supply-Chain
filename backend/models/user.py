from bson.objectid import ObjectId

class User:
    @staticmethod
    def find_by_email(db, email):
        user = db.users.find_one({"email": email})
        if user:
            return {
                "email": user.get("email"),
                "role": user.get("role"),
                "assignedProjects": user.get("assignedProjects", []),
                "createdProjects": user.get("createdProjects", []),
                "projectMetadata": user.get("projectMetadata", {})
            }
        return None

    @staticmethod
    def update_assigned_projects(db, email, project_data):
        result = db.users.update_one(
            {"email": email},
            {"$push": {"assignedProjects": project_data}}
        )
        return result.modified_count > 0