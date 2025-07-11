import React, { useEffect, useState } from "react";
import AdminCommitHistory from "./AdminCommitHistory";
import AdminRoleManager from "./AdminRoleManager";
import AdminCreateProject from "./AdminCreateProject";

function AdminDashboard() {
  const [user, setUser] = useState(null);

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
      <h2>Welcome, {user.username} (Admin)</h2>

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
