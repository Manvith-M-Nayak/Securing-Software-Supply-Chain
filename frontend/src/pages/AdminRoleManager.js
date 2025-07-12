import React, { useEffect, useState } from "react";

function AdminRoleManager({ user: parentUser }) {
  const [user, setUser]           = useState(parentUser || null);
  const [projects, setProjects]   = useState([]);
  const [users, setUsers]         = useState([]);

  const [selectedProject, setSelectedProject] = useState("");
  const [selectedUser,    setSelectedUser]    = useState("");
  const [selectedRole,    setSelectedRole]    = useState("developer");
  const [status,          setStatus]          = useState("");

  /* --------------------------------------------------
     Load user from localStorage if not passed via props
  -------------------------------------------------- */
  useEffect(() => {
    if (!user) {
      const stored = localStorage.getItem("user");
      if (stored) {
        try { setUser(JSON.parse(stored)); }
        catch (e) { console.error("parse user failed", e); }
      }
    }
  }, [user]);

  /* --------------------------------------------------
     Fetch admin projects and all users
  -------------------------------------------------- */
  useEffect(() => {
    if (!user?.githubUsername) return;

    // 1) Fetch projects created by admin
    fetch(`http://localhost:5001/admin/commits/${user.githubUsername}`)
      .then(r => r.json())
      .then(d => {
        if (Array.isArray(d.projects)) setProjects(d.projects);
        else if (d.error) setStatus("❌ " + d.error);
      })
      .catch(err => {
        console.error(err);
        setStatus("❌ Error fetching projects.");
      });

    // 2) Fetch all users with developer/auditor roles
    const fetchUsers = async () => {
      try {
        console.log('Fetching users from: http://localhost:5001/admin/users');
        const response = await fetch('http://localhost:5001/admin/users');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Raw API response:', data); // Debug log
        
        // Handle response structure
        let usersList = [];
        if (Array.isArray(data)) {
          usersList = data;
        } else if (data.users && Array.isArray(data.users)) {
          usersList = data.users;
        }
        
        console.log('Extracted users list:', usersList); // Debug log
        
        // Filter only developer and auditor roles
        const filtered = usersList.filter(u => {
          console.log('Checking user:', u); // Debug individual users
          return u.role && ["developer", "auditor"].includes(u.role.toLowerCase());
        });
        
        console.log('Filtered users:', filtered); // Debug log
        setUsers(filtered);
        
        if (filtered.length === 0) {
          setStatus("⚠️ No developers or auditors found in the database.");
        }
        
      } catch (err) {
        console.error('Error fetching users:', err);
        setStatus(`❌ Error fetching users: ${err.message}`);
      }
    };

    fetchUsers();
  }, [user]);

  /* --------------------------------------------------
     Handle assignment
  -------------------------------------------------- */
  const handleAssign = async () => {
    if (!selectedProject || !selectedUser) {
      setStatus("❌ Select project and user.");
      return;
    }

    try {
      const res  = await fetch("http://localhost:5001/admin/assign_user_to_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: selectedProject,
          userId:    selectedUser,
          role:      selectedRole
        })
      });
      const data = await res.json();
      if (res.ok) {
        setStatus("✅ User assigned.");
        setSelectedProject(""); setSelectedUser(""); setSelectedRole("developer");
      } else setStatus("❌ " + (data.error || "Assignment failed."));
    } catch (e) {
      console.error(e);
      setStatus("❌ Network/server error.");
    }
  };

  /* -------------------------------------------------- */
  return (
    <div style={{ maxWidth:550, margin:"0 auto 30px", padding:20, border:"1px solid #ccc", borderRadius:6 }}>
      <h3>Assign Role to User</h3>

      {/* Project dropdown */}
      <label style={{display:"block",marginTop:10}}>Project</label>
      <select value={selectedProject}
              onChange={e=>setSelectedProject(e.target.value)}
              style={{width:"100%",padding:8,marginBottom:10}}>
        <option value="">-- Select Project --</option>
        {projects.map(p=>(
          <option key={p._id||p.id} value={p._id||p.id}>{p.projectName}</option>
        ))}
      </select>

      {/* User dropdown */}
      <label style={{display:"block"}}>User</label>
      <select value={selectedUser}
              onChange={e=>setSelectedUser(e.target.value)}
              style={{width:"100%",padding:8,marginBottom:10}}>
        <option value="">-- Select User --</option>
        {users.map(u=>(
          <option key={u.userId||u.id||u._id}
                  value={u.userId||u.id||u._id}>
            {u.username || u.email} ({u.role})
          </option>
        ))}
      </select>

      {/* Role dropdown (what role to assign) */}
      <label style={{display:"block"}}>Role</label>
      <select value={selectedRole}
              onChange={e=>setSelectedRole(e.target.value)}
              style={{width:"100%",padding:8,marginBottom:15}}>
        <option value="developer">Developer</option>
        <option value="auditor">Auditor</option>
      </select>

      <button onClick={handleAssign}
              style={{padding:"10px 25px",background:"#007bff",color:"#fff",border:"none",borderRadius:4}}>
        Assign
      </button>

      {status && <p style={{marginTop:12,color:status.startsWith("✅")?"green":"red"}}>{status}</p>}
    </div>
  );
}

export default AdminRoleManager;