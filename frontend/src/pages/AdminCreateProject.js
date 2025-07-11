import React, { useEffect, useState } from "react";

function AdminCreateProject({ user: parentUser }) {
  // If the parent has already passed a user prop, use it; otherwise fall back to localStorage.
  const [user, setUser] = useState(parentUser || null);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [status, setStatus] = useState("");

  // Load user from localStorage on first mount (if not provided by props)
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

  // ---------- create project ----------
  const handleCreate = async () => {
    if (!user?.githubUsername) {
      setStatus("❌ Admin GitHub username not found.");
      return;
    }
    if (!name.trim() || !desc.trim()) {
      setStatus("❌ Project name and description are required.");
      return;
    }

    try {
      const res = await fetch("http://localhost:5001/admin/create_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description: desc.trim(),
          adminGithubUsername: user.githubUsername,
          createdAt: new Date().toISOString()
        })
      });

      const data = await res.json();
      if (res.ok) {
        setStatus("✅ Project created.");
        setName("");
        setDesc("");
      } else {
        setStatus("❌ " + (data.error || "Failed to create project."));
      }
    } catch (err) {
      console.error("Create project error:", err);
      setStatus("❌ Network / server error.");
    }
  };

  return (
    <div style={{ maxWidth: 550, margin: "0 auto 30px", padding: 20, border: "1px solid #ccc", borderRadius: 6 }}>
      <h3>Create New Project</h3>

      <input
        placeholder="Project Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />
      <textarea
        placeholder="Description"
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        rows={3}
        style={{ width: "100%", padding: 10, marginBottom: 10 }}
      />

      <button
        onClick={handleCreate}
        style={{ padding: "10px 25px", backgroundColor: "#007bff", color: "#fff", border: "none", borderRadius: 4 }}
      >
        Create
      </button>

      {status && <p style={{ marginTop: 12, color: status.startsWith("✅") ? "green" : "red" }}>{status}</p>}
    </div>
  );
}

export default AdminCreateProject;
