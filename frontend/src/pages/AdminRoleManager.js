import React, { useEffect, useState, useCallback } from "react";

function AdminRoleManager({ user: parentUser }) {
  const [user, setUser] = useState(parentUser || null);
  const [projects, setProjects] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedRole, setSelectedRole] = useState("developer");
  const [status, setStatus] = useState("");

  /* --------------------------------------------------
     Load user from localStorage if not passed via props
  -------------------------------------------------- */
  useEffect(() => {
    if (!user) {
      const stored = localStorage.getItem("user");
      if (stored) {
        try {
          const parsedUser = JSON.parse(stored);
          if (parsedUser.id && ObjectId.isValid(parsedUser.id) && parsedUser.role === "admin") {
            setUser(parsedUser);
            console.log("Loaded admin user:", parsedUser);
          } else {
            setStatus("❌ Invalid user data or not an admin. Please log in again.");
            console.log("Invalid user data:", parsedUser);
            window.location.href = "/login";
          }
        } catch (e) {
          console.error("Parse user failed:", e);
          setStatus("❌ Failed to parse user data. Please log in again.");
          window.location.href = "/login";
        }
      } else {
        setStatus("❌ No user data found. Please log in.");
        window.location.href = "/login";
      }
    }
  }, [user]);

  /* --------------------------------------------------
     Fetch admin projects and all users
  -------------------------------------------------- */
  const fetchProjectsAndUsers = useCallback(async () => {
    if (!user?.githubUsername) {
      console.log("No githubUsername for user:", user);
      return;
    }

    // 1) Fetch projects created by admin
    try {
      console.log(`Fetching projects from: http://localhost:5001/admin/commits/${user.githubUsername}`);
      const projectRes = await fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`);
      if (!projectRes.ok) {
        const errorData = await projectRes.json();
        throw new Error(errorData.error || `HTTP ${projectRes.status}: ${projectRes.statusText}`);
      }
      const projectData = await projectRes.json();
      console.log("Projects response:", projectData);
      if (Array.isArray(projectData.projects)) {
        const validProjects = projectData.projects.filter(p => p.name && typeof p.name === "string");
        setProjects(validProjects);
        if (validProjects.length > 0) {
          setSelectedProject(validProjects[0].name);
          console.log("Initial selected project:", validProjects[0].name);
        } else {
          setStatus("⚠️ No projects found for this admin.");
        }
      } else {
        throw new Error(projectData.error || "Invalid projects response format");
      }
    } catch (err) {
      console.error("Error fetching projects:", err);
      setStatus(`❌ Error fetching projects: ${err.message}`);
    }

    // 2) Fetch all available users
    try {
      console.log("Fetching users from: http://localhost:5001/admin/available_users");
      const userRes = await fetch("http://localhost:5001/admin/available_users");
      if (!userRes.ok) {
        const errorData = await userRes.json();
        throw new Error(errorData.error || `HTTP ${userRes.status}: ${userRes.statusText}`);
      }
      const userData = await userRes.json();
      console.log("Users response:", userData);
      let usersList = [];
      if (Array.isArray(userData)) {
        usersList = userData;
      } else if (userData.users && Array.isArray(userData.users)) {
        usersList = userData.users;
      } else {
        throw new Error("Invalid users response format");
      }
      const filtered = usersList.filter(u => {
        console.log("Checking user:", u);
        return u.role && ["developer", "auditor"].includes(u.role.toLowerCase()) && u._id && u.githubUsername;
      });
      console.log("Filtered users:", filtered);
      setUsers(filtered);
      if (filtered.length === 0) {
        setStatus("⚠️ No developers or auditors found in the database.");
      }
    } catch (err) {
      console.error("Error fetching users:", err);
      setStatus(`❌ Error fetching users: ${err.message}`);
    }
  }, [user]);

  useEffect(() => {
    if (user?.githubUsername) {
      fetchProjectsAndUsers();
    }
  }, [user, fetchProjectsAndUsers]);

  /* --------------------------------------------------
     Send GitHub collaborator invitation
  -------------------------------------------------- */
  const sendGitHubInvitation = async (projectName, githubUsername, githubToken, inviteeUsername) => {
    const invitationUrl = `https://api.github.com/repos/${githubUsername}/${projectName}/collaborators/${inviteeUsername}`;
    try {
      console.log(`Sending GitHub invitation for ${inviteeUsername} to ${projectName}`);
      const res = await fetch(invitationUrl, {
        method: "PUT",
        headers: {
          Authorization: `token ${githubToken}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify({
          permission: selectedRole === "developer" ? "push" : "pull",
        }),
      });

      if (!res.ok) {
        let errorMessage = "Failed to send GitHub invitation";
        try {
          const errorData = await res.json();
          errorMessage = errorData.message || errorMessage;
          if (res.status === 401) {
            errorMessage = "Invalid GitHub token. Please check your token permissions.";
          } else if (res.status === 404) {
            errorMessage = "Repository or user not found on GitHub.";
          } else if (res.status === 422) {
            errorMessage = "User is already a collaborator or invitation is pending.";
          }
        } catch (jsonError) {
          const text = await res.text();
          errorMessage = text || errorMessage;
        }
        throw new Error(errorMessage);
      }

      try {
        return await res.json();
      } catch (jsonError) {
        if (res.status === 204) {
          return { message: "No content returned, invitation likely successful" };
        }
        throw new Error("Failed to parse GitHub response");
      }
    } catch (err) {
      console.error("GitHub invitation error:", err);
      throw new Error(`GitHub invitation error: ${err.message}`);
    }
  };

  /* --------------------------------------------------
     Handle assignment
  -------------------------------------------------- */
  const handleAssign = async () => {
    if (!selectedProject || !selectedUser || !projects.find(p => p.name === selectedProject)) {
      setStatus("❌ Select a valid project and user.");
      console.log("Invalid assignment attempt:", { selectedProject, selectedUser, projects });
      return;
    }

    try {
      const selectedUserData = users.find((u) => u._id === selectedUser);
      if (!selectedUserData?.githubUsername) {
        setStatus("❌ Selected user has no GitHub username.");
        console.log("No githubUsername for user:", selectedUserData);
        return;
      }

      // Assign user to project in backend
      console.log(`Assigning user ${selectedUser} to project ${selectedProject} as ${selectedRole}`);
      const assignRes = await fetch("http://localhost:5001/admin/assign_user_to_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectName: selectedProject,
          userId: selectedUser,
          role: selectedRole,
          assignedAt: new Date().toISOString(),
        }),
      });
      const assignData = await assignRes.json();

      if (!assignRes.ok) {
        throw new Error(assignData.error || "Assignment failed");
      }

      // Initialize points for developer in the project
      if (selectedRole === "developer") {
        console.log(`Initializing points for user ${selectedUser} in project ${selectedProject}`);
        const pointsRes = await fetch(`http://localhost:5001/api/users/${selectedUser}/points`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            projectName: selectedProject,
            points: 0
          }),
        });
        const pointsData = await pointsRes.json();
        if (!pointsRes.ok) {
          throw new Error(pointsData.error || "Failed to initialize user points");
        }
      }

      // Send GitHub collaborator invitation
      setStatus("📩 Sending GitHub invitation...");
      await sendGitHubInvitation(
        selectedProject,
        user.githubUsername,
        user.githubToken,
        selectedUserData.githubUsername
      );

      setStatus("✅ User assigned and GitHub invitation sent successfully.");
      console.log(`Assignment successful: ${selectedUserData.username} to ${selectedProject} as ${selectedRole}`);
      setSelectedProject("");
      setSelectedUser("");
      setSelectedRole("developer");
      fetchProjectsAndUsers();
    } catch (e) {
      console.error("Assignment error:", e);
      setStatus(`❌ ${e.message}`);
    }
  };

  /* --------------------------------------------------
     Handle removal
  -------------------------------------------------- */
  const handleRemove = async (projectName, userId) => {
    if (!window.confirm("Are you sure you want to remove this user from the project?")) {
      return;
    }

    try {
      console.log(`Removing user ${userId} from project ${projectName}`);
      const res = await fetch("http://localhost:5001/admin/remove_user_from_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectName,
          userId,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setStatus("✅ User removed successfully from project.");
        console.log(`Removal successful: user ${userId} from ${projectName}`);
        fetchProjectsAndUsers();
      } else {
        throw new Error(data.error || "Removal failed");
      }
    } catch (e) {
      console.error("Removal error:", e);
      setStatus(`❌ ${e.message}`);
    }
  };

  /* --------------------------------------------------
     Mock ObjectId validation for frontend
  -------------------------------------------------- */
  const ObjectId = {
    isValid: (id) => /^[0-9a-fA-F]{24}$/.test(id)
  };

  /* -------------------------------------------------- */
  return (
    <div
      style={{ maxWidth: 800, margin: "0 auto 30px", padding: 20, border: "1px solid #ccc", borderRadius: 6 }}
    >
      <h3>Assign Role to User</h3>

      {/* Assignment Form */}
      <div style={{ marginBottom: 30, padding: 15, background: "#f8f9fa", borderRadius: 4 }}>
        {/* Project dropdown */}
        <label style={{ display: "block", marginTop: 10 }}>Project</label>
        <select
          value={selectedProject}
          onChange={(e) => {
            const value = e.target.value;
            if (projects.find(p => p.name === value)) {
              setSelectedProject(value);
              console.log("Selected project:", value);
            } else {
              setSelectedProject("");
              setStatus("❌ Invalid project selected.");
              console.log("Invalid project selection:", value);
            }
          }}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        >
          <option value="">-- Select Project --</option>
          {projects.map((p) => (
            <option key={p._id || p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>

        {/* User dropdown */}
        <label style={{ display: "block" }}>User</label>
        <select
          value={selectedUser}
          onChange={(e) => {
            const value = e.target.value;
            if (users.find(u => u._id === value)) {
              setSelectedUser(value);
              console.log("Selected user:", value);
            } else {
              setSelectedUser("");
              setStatus("❌ Invalid user selected.");
              console.log("Invalid user selection:", value);
            }
          }}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        >
          <option value="">-- Select User --</option>
          {users.map((u) => (
            <option key={u._id} value={u._id}>
              {u.username || u.email} ({u.role}{u.role === 'developer' ? `, Points: ${u.points?.[selectedProject] || 0}` : ''}) - {u.githubUsername}
            </option>
          ))}
        </select>

        {/* Role dropdown */}
        <label style={{ display: "block" }}>Role</label>
        <select
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 15 }}
        >
          <option value="developer">Developer</option>
          <option value="auditor">Auditor</option>
        </select>

        <button
          onClick={handleAssign}
          disabled={!selectedProject || !selectedUser}
          style={{
            padding: "10px 25px",
            background: "#007bff",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            marginRight: 10,
            opacity: (!selectedProject || !selectedUser) ? 0.5 : 1,
            cursor: (!selectedProject || !selectedUser) ? "not-allowed" : "pointer",
          }}
        >
          Assign
        </button>

        <button
          onClick={fetchProjectsAndUsers}
          style={{
            padding: "10px 25px",
            background: "#28a745",
            color: "#fff",
            border: "none",
            borderRadius: 4,
          }}
        >
          Refresh Projects
        </button>
      </div>

      {/* Current Assignments Display */}
      <div>
        <h4>Current Project Assignments</h4>
        {projects.length === 0 ? (
          <p style={{ color: "#666", fontStyle: "italic" }}>No projects found.</p>
        ) : (
          projects.map((project) => (
            <div
              key={project._id}
              style={{
                border: "1px solid #ddd",
                borderRadius: 4,
                padding: 15,
                marginBottom: 15,
                background: "#fff",
              }}
            >
              <h5 style={{ margin: "0 0 10px 0", color: "#333" }}>{project.name}</h5>
              {project.assignedUsers && project.assignedUsers.length > 0 ? (
                <div>
                  <strong>Assigned Users:</strong>
                  <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                    {project.assignedUsers.map((assignment, index) => (
                      <li
                        key={index}
                        style={{
                          marginBottom: 8,
                          padding: "8px 12px",
                          background: "#f8f9fa",
                          borderRadius: 3,
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <span>
                          <strong>{assignment.username}</strong> ({assignment.githubUsername}) -
                          <span
                            style={{
                              color: assignment.role === "developer" ? "#007bff" : "#28a745",
                              fontWeight: "bold",
                            }}
                          >
                            {assignment.role}
                          </span>
                          {assignment.points !== null && (
                            <span style={{ color: "#666", fontSize: "0.9em" }}>
                              {" "}• Points: {assignment.points?.[project.name] || 0}
                            </span>
                          )}
                          {assignment.assignedAt && (
                            <span style={{ color: "#666", fontSize: "0.9em" }}>
                              {" "}• Assigned: {new Date(assignment.assignedAt).toLocaleDateString()}
                            </span>
                          )}
                        </span>
                        <button
                          onClick={() => handleRemove(project.name, assignment.userId)}
                          style={{
                            padding: "4px 8px",
                            background: "#dc3545",
                            color: "#fff",
                            border: "none",
                            borderRadius: 3,
                            fontSize: "0.8em",
                            cursor: "pointer",
                          }}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p style={{ color: "#666", fontStyle: "italic" }}>No users assigned to this project.</p>
              )}
            </div>
          ))
        )}
      </div>

      {status && (
        <p style={{ marginTop: 12, color: status.startsWith("✅") || status.startsWith("📩") ? "green" : "red" }}>
          {status}
        </p>
      )}
    </div>
  );
}

export default AdminRoleManager;