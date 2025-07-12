import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AdminCommitHistory from "./AdminCommitHistory";
import AdminRoleManager from "./AdminRoleManager";
import AdminCreateProject from "./AdminCreateProject";

function AdminDashboard() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Retrieve user info from localStorage
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      } catch (err) {
        console.error("Failed to parse user from localStorage:", err);
      }
    } else {
      console.warn("No user found in localStorage");
    }
  }, []);

  const handleLogout = () => {
    // Clear user data from localStorage
    localStorage.removeItem("user");
    // Clear local state
    setUser(null);
    // Redirect to login page
    navigate("/");
  };

  if (!user) {
    return (
      <div style={{ padding: "20px", fontFamily: "Arial", color: "red" }}>
        <h2>⚠️ User not logged in</h2>
        <p>Please login again to continue.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" }}>
        <h2>Welcome, {user.username} (Admin)</h2>
        <button
          onClick={handleLogout}
          style={{
            padding: "10px 20px",
            backgroundColor: "#dc3545",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "bold"
          }}
          onMouseOver={(e) => e.target.style.backgroundColor = "#c82333"}
          onMouseOut={(e) => e.target.style.backgroundColor = "#dc3545"}
        >
          Logout
        </button>
      </div>

      <div style={{ marginBottom: "30px" }}>
        <AdminCreateProject user={user} />
      </div>

      <div style={{ marginBottom: "30px" }}>
        <AdminRoleManager user={user} />
      </div>

      <div style={{ marginBottom: "30px" }}>
        <AdminCommitHistory user={user} />
      </div>
    </div>
  );
}

export default AdminDashboard;