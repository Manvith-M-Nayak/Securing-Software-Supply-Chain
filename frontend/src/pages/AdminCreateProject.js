import React, { useState, useEffect } from "react";

function AdminCreateProject() {
  // Step 1: Initialize userData as null
  const [userData, setUserData] = useState(null);
  
  // Step 2: Simulate loading userData (since localStorage isn't available in artifacts)
  useEffect(() => {
    // Simulating localStorage data - in real app, this would come from localStorage
    const simulatedUserData = {
      githubUsername: "admin-user",
      username: "Admin User",
      githubToken: "ghp_xxxxxxxxxxxxxxxxxxxx" // This would be stored securely
    };
    
    setUserData(simulatedUserData);
    console.log("✅ userData loaded:", simulatedUserData);
  }, []);

  const [name, setName] = useState("");
  const [status, setStatus] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  // Function to create GitHub repository
  const createGitHubRepo = async (projectName, githubUsername, githubToken) => {
    try {
      // Create the repository
      const repoResponse = await fetch(`https://api.github.com/user/repos`, {
        method: 'POST',
        headers: {
          'Authorization': `token ${githubToken}`,
          'Content-Type': 'application/json',
          'Accept': 'application/vnd.github.v3+json'
        },
        body: JSON.stringify({
          name: projectName,
          description: `Project repository for ${projectName}`,
          private: false, // Set to true if you want private repos
          auto_init: true, // Initialize with README
          gitignore_template: 'Node', // Optional: add .gitignore template
        })
      });

      if (!repoResponse.ok) {
        const errorData = await repoResponse.json();
        throw new Error(errorData.message || 'Failed to create repository');
      }

      const repoData = await repoResponse.json();
      console.log('✅ GitHub repository created:', repoData.html_url);
      
      return repoData;
    } catch (error) {
      console.error('❌ GitHub repository creation error:', error);
      throw error;
    }
  };

  // Function to set up webhook
  const setupWebhook = async (githubUsername, projectName, githubToken, webhookUrl) => {
    try {
      const webhookResponse = await fetch(
        `https://api.github.com/repos/${githubUsername}/${projectName}/hooks`,
        {
          method: 'POST',
          headers: {
            'Authorization': `token ${githubToken}`,
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github.v3+json'
          },
          body: JSON.stringify({
            name: 'web',
            active: true,
            events: [
              'push',
              'pull_request',
              'issues',
              'issue_comment',
              'commit_comment',
              'create',
              'delete',
              'fork',
              'release'
            ],
            config: {
              url: webhookUrl,
              content_type: 'json',
              insecure_ssl: '0' // Use '1' for insecure SSL if needed
            }
          })
        }
      );

      if (!webhookResponse.ok) {
        const errorData = await webhookResponse.json();
        throw new Error(errorData.message || 'Failed to create webhook');
      }

      const webhookData = await webhookResponse.json();
      console.log('✅ Webhook created:', webhookData.id);
      
      return webhookData;
    } catch (error) {
      console.error('❌ Webhook creation error:', error);
      throw error;
    }
  };

  // Function to handle project creation
  const handleCreate = async () => {
    if (!userData || !userData.githubUsername) {
      setStatus("❌ Admin GitHub username not found. Please ensure user data is loaded correctly.");
      return;
    }

    if (!name.trim()) {
      setStatus("❌ Please enter a project name.");
      return;
    }

    setIsCreating(true);
    setStatus("🔄 Creating project and setting up GitHub integration...");

    try {
      // Step 1: Create the project in your backend
      const projectData = {
        name: name.trim(),
        adminGithubUsername: userData.githubUsername,
        createdAt: new Date().toISOString(),
      };

      const res = await fetch("http://localhost:5001/admin/create_project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectData),
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || "Failed to create project in database");
      }

      setStatus("✅ Project created in database. Setting up GitHub repository...");

      // Step 2: Create GitHub repository (if GitHub token is available)
      if (userData.githubToken) {
        try {
          const repoData = await createGitHubRepo(
            name.trim(),
            userData.githubUsername,
            userData.githubToken
          );

          setStatus("✅ GitHub repository created. Setting up webhook...");

          // Step 3: Set up webhook
          const webhookUrl = `http://localhost:5001/webhook/${data.projectId || name.trim()}`;
          
          await setupWebhook(
            userData.githubUsername,
            name.trim(),
            userData.githubToken,
            webhookUrl
          );

          // Step 4: Update project with GitHub info
          await fetch(`http://localhost:5001/admin/update_project`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              projectId: data.projectId || name.trim(),
              githubRepoUrl: repoData.html_url,
              githubRepoId: repoData.id,
              webhookConfigured: true
            }),
          });

          setStatus(`✅ Project created successfully! GitHub repository: ${repoData.html_url}`);
        } catch (githubError) {
          console.error("GitHub setup error:", githubError);
          setStatus(`⚠️ Project created but GitHub setup failed: ${githubError.message}`);
        }
      } else {
        setStatus("✅ Project created successfully! (GitHub token not available for auto-setup)");
      }

      setName(""); // Reset input field
    } catch (err) {
      console.error("❌ Create project error:", err);
      setStatus("❌ " + (err.message || "Network or server error."));
    } finally {
      setIsCreating(false);
    }
  };

  // Show loading UI if userData not yet loaded
  if (!userData) {
    return (
      <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
        <h2>Create New Project</h2>
        <div>Loading user data...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h2>Create New Project</h2>
      
      <input
        type="text"
        placeholder="Project Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ 
          width: "100%", 
          padding: 10, 
          marginBottom: 10,
          border: "1px solid #ddd",
          borderRadius: 4
        }}
        disabled={isCreating}
      />
      
      <button
        onClick={handleCreate}
        disabled={isCreating || !name.trim()}
        style={{
          padding: "10px 20px",
          backgroundColor: isCreating ? "#ccc" : "#007bff",
          color: "white",
          border: "none",
          borderRadius: 4,
          cursor: isCreating ? "not-allowed" : "pointer"
        }}
      >
        {isCreating ? "Creating..." : "Create Project & GitHub Repo"}
      </button>
      
      {status && (
        <div style={{ 
          marginTop: 10, 
          padding: 10, 
          backgroundColor: status.includes("❌") ? "#ffebee" : status.includes("⚠️") ? "#fff3e0" : "#e8f5e8",
          border: "1px solid " + (status.includes("❌") ? "#f44336" : status.includes("⚠️") ? "#ff9800" : "#4caf50"),
          borderRadius: 4
        }}>
          {status}
        </div>
      )}

      {process.env.NODE_ENV === "development" && (
        <div style={{ 
          marginTop: 20, 
          padding: 10, 
          backgroundColor: "#f5f5f5",
          fontSize: 12,
          borderRadius: 4
        }}>
          <strong>Debug Info:</strong><br/>
          User from state: {userData ? "Yes" : "No"}<br/>
          GitHub Username: {userData?.githubUsername || "Not found"}<br/>
          Username: {userData?.username || "Not found"}<br/>
          GitHub Token: {userData?.githubToken ? "Available" : "Not available"}<br/>
          User object keys: {userData ? Object.keys(userData).join(", ") : "No user"}
        </div>
      )}
    </div>
  );
}

export default AdminCreateProject;