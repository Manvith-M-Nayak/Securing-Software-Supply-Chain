import React, { useEffect, useState } from "react";

function AdminRoleManager({ user: parentUser }) {
  const [user, setUser] = useState(parentUser || null);
  const [projects, setProjects] = useState([]);
  const [users, setUsers] = useState([]);

  const [selectedProject, setSelectedProject] = useState("");
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedRole, setSelectedRole] = useState("developer");
  const [status, setStatus] = useState("");

  // --------------------------------------------------
  // Load user from localStorage if not provided via props
  useEffect(() => {
    if (!user) {
      const stored = localStorage.getItem("user");
      if (stored) {
        try {
          setUser(JSON.parse(stored));
        } catch (e) {
          console.error("Failed to parse user from localStorage", e);
        }
      }
    }
  }, [user]);

  // --------------------------------------------------
  // Fetch projects & pending users once we know admin GitHub username
  useEffect(() => {
    if (!user?.githubUsername) return;

    // 1. fetch projects created by this admin
    fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.projects) setProjects(data.projects);
        else if (data.error) setStatus("❌ " + data.error);
      })
      .catch((e) => {
        console.error(e);
        setStatus("❌ Error fetching projects.");
      });

    // 2. fetch user access requests
    //    (❗ adjust if your backend expects a query param)
    fetch(`http://localhost:5001/admin/access_requests?adminGithubUsername=${user.githubUsername}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.requests) setUsers(data.requests);
        else if (data.error) setStatus("❌ " + data.error);
      })
      .catch((e) => {
        console.error(e);
        setStatus("❌ Error fetching user requests.");
      });
  }, [user]);

  // --------------------------------------------------
  // Assign user to project
  const handleAssign = async () => {
    if (!selectedProject || !selectedUser) {
      setStatus("❌ Select a project and a user.");
      return;
    }

    try {
      const res = await fetch("http://localhost:5001/admin/assign_user_to_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: selectedProject,
          userId: selectedUser,
          role: selectedRole
        })
      });

      const data = await res.json();
      if (res.ok) {
        setStatus("✅ User assigned.");
        // optional reset:
        setSelectedProject("");
        setSelectedUser("");
        setSelectedRole("developer");
      } else {
        setStatus("❌ " + (data.error || "Assignment failed."));
      }
    } catch (err) {
      console.error("Assign error:", err);
      setStatus("❌ Network / server error.");
    }
  };

  // --------------------------------------------------
  return (
    <div style={{ maxWidth: 550, margin: "0 auto 30px", padding: 20, border: "1px solid #ccc", borderRadius: 6 }}>
      <h3>Assign Role to User</h3>

      {/* Project Select */}
      <label style={{ display: "block", marginTop: 10 }}>Project</label>
      <select
        value={selectedProject}
        onChange={(e) => setSelectedProject(e.target.value)}
        style={{ width: "100%", padding: 8, marginBottom: 10 }}
      >
        <option value="">-- Select Project --</option>
        {projects.map((p) => (
          <option key={p._id || p.id} value={p._id || p.id}>
            {p.projectName}
          </option>
        ))}
      </select>

      {/* User Select */}
      <label style={{ display: "block" }}>User</label>
      <select
        value={selectedUser}
        onChange={(e) => setSelectedUser(e.target.value)}
        style={{ width: "100%", padding: 8, marginBottom: 10 }}
      >
        <option value="">-- Select User --</option>
        {users.map((u) => (
          <option key={u.userId || u.id} value={u.userId || u.id}>
            {u.username || u.email}
          </option>
        ))}
      </select>

      {/* Role Select */}
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
        style={{ padding: "10px 25px", backgroundColor: "#007bff", color: "#fff", border: "none", borderRadius: 4 }}
      >
        Assign
      </button>

      {status && <p style={{ marginTop: 12, color: status.startsWith("✅") ? "green" : "red" }}>{status}</p>}
    </div>
  );
}

export default AdminRoleManager;
