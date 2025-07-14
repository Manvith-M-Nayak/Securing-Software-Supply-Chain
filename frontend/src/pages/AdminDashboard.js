import React, { useEffect, useState } from "react";
import AdminCommitHistory from "./AdminCommitHistory";
import AdminRoleManager from "./AdminRoleManager";
import AdminCreateProject from "./AdminCreateProject";

function AdminDashboard() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Retrieve user info from localStorage
    const userData = JSON.parse(localStorage.getItem('user'));
    if (userData) {
      setUser(userData);
    } else {
      console.warn("No user found in localStorage");
      // If no user, redirect to login immediately
      window.location.href = "/";
      return;
    }
  }, []);

  const handleLogout = () => {
    try {
      // Clear user data from localStorage
      localStorage.removeItem("user");
      // Clear local state
      setUser(null);
      // Force redirect to login page with window.location for immediate redirect
      window.location.href = "/";
    } catch (err) {
      console.error("Error during logout:", err);
      // Even if there's an error, still try to navigate
      window.location.href = "/";
    }
  };

  // Don't render anything if user is null (should redirect anyway)
  if (!user) {
    return null;
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
        <AdminCreateProject />
      </div>

      <div style={{ marginBottom: "30px" }}>
        <AdminRoleManager />
      </div>

      <div style={{ marginBottom: "30px" }}>
        <AdminCommitHistory />
      </div>
    </div>
  );
}

export default AdminDashboard;