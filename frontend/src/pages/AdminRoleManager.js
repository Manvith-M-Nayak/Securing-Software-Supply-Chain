import React, { useEffect, useState } from "react";

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
          setUser(JSON.parse(stored));
        } catch (e) {
          console.error("parse user failed", e);
        }
      }
    }
  }, [user]);

  /* --------------------------------------------------
     Fetch admin projects and all users
  -------------------------------------------------- */
  useEffect(() => {
    if (!user?.githubUsername) return;

    // 1) Fetch projects created by admin (from admin's createdProjects array)
    fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`)
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d.projects)) setProjects(d.projects);
        else if (d.error) setStatus("❌ " + d.error);
      })
      .catch((err) => {
        console.error(err);
        setStatus("❌ Error fetching projects.");
      });

    // 2) Fetch all available users (developers and auditors)
    const fetchUsers = async () => {
      try {
        console.log("Fetching users from: http://localhost:5001/admin/available_users");
        const response = await fetch("http://localhost:5001/admin/available_users");

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Raw API response:", data); // Debug log

        // Handle response structure
        let usersList = [];
        if (Array.isArray(data)) {
          usersList = data;
        } else if (data.users && Array.isArray(data.users)) {
          usersList = data.users;
        }

        console.log("Extracted users list:", usersList); // Debug log

        // Filter only developer and auditor roles
        const filtered = usersList.filter((u) => {
          console.log("Checking user:", u); // Debug individual users
          return u.role && ["developer", "auditor"].includes(u.role.toLowerCase());
        });

        console.log("Filtered users:", filtered); // Debug log
        setUsers(filtered);

        if (filtered.length === 0) {
          setStatus("⚠️ No developers or auditors found in the database.");
        }
      } catch (err) {
        console.error("Error fetching users:", err);
        setStatus(`❌ Error fetching users: ${err.message}`);
      }
    };

    fetchUsers();
  }, [user]);

  /* --------------------------------------------------
     Send GitHub collaborator invitation
  -------------------------------------------------- */
  const sendGitHubInvitation = async (projectName, githubUsername, githubToken, inviteeUsername) => {
    const invitationUrl = `https://api.github.com/repos/${githubUsername}/${projectName}/collaborators/${inviteeUsername}`;
    try {
      const res = await fetch(invitationUrl, {
        method: "PUT",
        headers: {
          Authorization: `token ${githubToken}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify({
          permission: selectedRole === "developer" ? "push" : "pull", // Developers can push, auditors can only read
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to send GitHub invitation");
      }

      return await res.json();
    } catch (err) {
      throw new Error(`GitHub invitation error: ${err.message}`);
    }
  };

  /* --------------------------------------------------
     Handle assignment
  -------------------------------------------------- */
  const handleAssign = async () => {
    if (!selectedProject || !selectedUser) {
      setStatus("❌ Select project and user.");
      return;
    }

    try {
      // Find the selected user's GitHub username
      const selectedUserData = users.find((u) => u._id === selectedUser);
      if (!selectedUserData?.githubUsername) {
        setStatus("❌ Selected user has no GitHub username.");
        return;
      }

      // Assign user to project in backend
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

      // Send GitHub collaborator invitation
      setStatus("📩 Sending GitHub invitation...");
      await sendGitHubInvitation(
        selectedProject,
        user.githubUsername,
        user.githubToken,
        selectedUserData.githubUsername
      );

      setStatus("✅ User assigned and GitHub invitation sent successfully.");
      setSelectedProject("");
      setSelectedUser("");
      setSelectedRole("developer");
      // Refresh projects to show updated assignments
      refreshProjects();
    } catch (e) {
      console.error(e);
      setStatus(`❌ ${e.message}`);
    }
  };

  /* --------------------------------------------------
     Handle removal
  -------------------------------------------------- */
  const handleRemove = async (projectId, userId) => {
    if (!window.confirm("Are you sure you want to remove this user from the project?")) {
      return;
    }

    try {
      const res = await fetch("http://localhost:5001/admin/remove_user_from_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectName: projectId, // Corrected to use projectName
          userId: userId,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setStatus("✅ User removed successfully from both project and user records.");
        refreshProjects();
      } else {
        setStatus("❌ " + (data.error || "Removal failed."));
      }
    } catch (e) {
      console.error(e);
      setStatus("❌ Network/server error.");
    }
  };

  /* --------------------------------------------------
     Refresh projects data
  -------------------------------------------------- */
  const refreshProjects = () => {
    if (!user?.githubUsername) return;

    fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`)
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d.projects)) setProjects(d.projects);
        else if (d.error) setStatus("❌ " + d.error);
      })
      .catch((err) => {
        console.error(err);
        setStatus("❌ Error refreshing projects.");
      });
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
          onChange={(e) => setSelectedProject(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        >
          <option value="">-- Select Project --</option>
          {projects.map((p) => (
            <option key={p._id || p.id} value={p._id || p.id}>
              {p.name || p.projectName}
            </option>
          ))}
        </select>

        {/* User dropdown */}
        <label style={{ display: "block" }}>User</label>
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          style={{ width: "100%", padding: 8, marginBottom: 10 }}
        >
          <option value="">-- Select User --</option>
          {users.map((u) => (
            <option key={u._id} value={u._id}>
              {u.username || u.email} ({u.role}) - {u.githubUsername}
            </option>
          ))}
        </select>

        {/* Role dropdown (what role to assign) */}
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
          style={{
            padding: "10px 25px",
            background: "#007bff",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            marginRight: 10,
          }}
        >
          Assign
        </button>

        <button
          onClick={refreshProjects}
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
              <h5 style={{ margin: "0 0 10px 0", color: "#333" }}>{project.name || project.projectName}</h5>

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
                          {assignment.assignedAt && (
                            <span style={{ color: "#666", fontSize: "0.9em" }}>
                              {" "}• Assigned: {new Date(assignment.assignedAt).toLocaleDateString()}
                            </span>
                          )}
                        </span>
                        <button
                          onClick={() => handleRemove(project._id, assignment.userId)}
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