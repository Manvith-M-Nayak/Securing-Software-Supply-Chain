import React, { useEffect, useState } from "react";

function AdminCommitHistory() {
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  // Get user from localStorage on component mount
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      } else {
        setStatus("❌ No user found in localStorage.");
        setLoading(false);
      }
    } catch (error) {
      console.error("Error parsing user from localStorage:", error);
      setStatus("❌ Error reading user data from localStorage.");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchProjects = async () => {
      if (!user || !user.githubUsername) {
        setStatus("❌ Admin GitHub username not available.");
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`);
        const data = await res.json();

        if (res.ok && Array.isArray(data.projects)) {
          setProjects(data.projects);
          setStatus(""); // No error
        } else {
          const message = data.error || "❌ Failed to fetch projects.";
          setStatus(message);
        }
      } catch (err) {
        console.error("Error fetching projects:", err);
        setStatus("❌ Failed to connect to backend.");
      } finally {
        setLoading(false);
      }
    };

    // Only fetch projects if user is available
    if (user) {
      fetchProjects();
    }
  }, [user]);

  return (
    <div style={{ padding: "1rem", fontFamily: "Arial" }}>
      <h3>
        Projects Created by <span style={{ color: "#007bff" }}>{user?.username || "Admin"}</span>
      </h3>

      {loading && <p>Loading projects...</p>}

      {!loading && status && (
        <p style={{ color: "red", fontWeight: "bold" }}>{status}</p>
      )}

      {!loading && !status && projects.length === 0 && (
        <p>No projects found.</p>
      )}

      {!loading && !status && projects.map((project, idx) => (
        <div
          key={idx}
          style={{
            border: "1px solid #ccc",
            borderRadius: "5px",
            padding: "12px",
            marginBottom: "15px",
            backgroundColor: "#f9f9f9"
          }}
        >
          <h4 style={{ marginBottom: "5px", color: "#333" }}>{project.projectName}</h4>
          <p style={{ margin: "5px 0", color: "#555" }}>{project.description}</p>

          {Array.isArray(project.assignedUsers) && project.assignedUsers.length > 0 ? (
            <div>
              <strong>Assigned Users:</strong>
              <ul>
                {project.assignedUsers.map((user, i) => (
                  <li key={i}>
                    User ID: <code>{user.userId}</code> — Role: <strong>{user.role}</strong>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p style={{ fontStyle: "italic" }}>No users assigned yet.</p>
          )}
        </div>
      ))}
    </div>
  );
}

export default AdminCommitHistory;