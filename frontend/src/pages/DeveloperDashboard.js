import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5001";

function DeveloperDashboard() {
  const [pullRequests, setPullRequests] = useState([]);
  const [status, setStatus] = useState("Loading...");
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");

  // Load user
  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem("user"));
      if (u) {
        setUser(u);
        console.log("Loaded user:", u);
      } else {
        setStatus("User not logged in.");
      }
    } catch (err) {
      console.error("User load failed", err);
      setStatus("Failed to load user.");
    }
  }, []);

  // Fetch projects
  useEffect(() => {
    if (!user) return;

    const fetchProjects = async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/api/projects`);
        const projectNames = data.map(p => p.projectName || p.name).filter(Boolean);
        setProjects(projectNames);
        if (projectNames.length > 0) {
          setSelectedProject(projectNames[0]); // Default to first project
        }
      } catch (err) {
        console.error("Project fetch failed", err);
      }
    };

    fetchProjects();
  }, [user]);

  // Fetch all pull requests
  useEffect(() => {
    if (!user) return;

    const fetchPullRequests = async () => {
      try {
        console.log("Fetching pull requests for user:", user.githubUsername || user.username);
        const { data } = await axios.get(`${API_BASE_URL}/api/pullrequests`);
        console.log("Raw API response:", data);
        const uniquePullRequests = Array.from(new Map(data.map(pr => [JSON.stringify([pr.pullRequestId, pr.projectName]), pr])).values());
        console.log("Unique pull requests:", uniquePullRequests);
        setPullRequests(uniquePullRequests);
        if (Array.isArray(uniquePullRequests) && uniquePullRequests.length > 0) {
          setStatus("Loaded.");
        } else {
          setStatus("No pull requests found.");
        }
      } catch (err) {
        console.error("Pull request fetch failed", err);
        setStatus(`Failed to fetch pull requests: ${err.message}`);
      }
    };

    fetchPullRequests();
    const interval = setInterval(fetchPullRequests, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const userPullRequests = pullRequests.filter((pr) => {
    const name = user?.githubUsername?.toLowerCase() || user?.username?.toLowerCase();
    const dName = pr.developer?.toLowerCase() || "";
    const projectMatch = !selectedProject || pr.projectName === selectedProject;
    const matches = dName === name && projectMatch;
    console.log(`Filtering PR ${pr.pullRequestId} (${pr.projectName}): developer=${dName}, projectMatch=${projectMatch}, matches=${matches}`);
    return matches;
  });

  const pullRequestCount = userPullRequests.length;
  const pullRequestStatuses = userPullRequests.reduce((acc, pr) => {
    acc[pr.status] = (acc[pr.status] || 0) + 1;
    return acc;
  }, { pending: 0, approved: 0, rejected: 0 });

  const fmt = (t) => new Date(t).toLocaleString();

  return (
    <div className="min-h-screen bg-gray-100 p-6 font-sans">
      <header className="bg-white shadow p-4 rounded mb-6 flex justify-between">
        <div>
          <h1 className="text-2xl font-bold">Developer Dashboard</h1>
          <p className="text-gray-600">Logged in as: {user?.username || "..."}</p>
        </div>
        <button
          onClick={() => {
            localStorage.clear();
            window.location.href = "/login";
          }}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          Logout
        </button>
      </header>

      <main className="bg-white p-6 rounded shadow">
        <section className="mb-6">
          <h2 className="text-xl font-semibold mb-2">Pull Request Overview</h2>
          <p className="text-gray-700">Total Pull Requests: {pullRequestCount}</p>
          <div className="mt-2">
            <p className="text-gray-700">Status Breakdown:</p>
            <ul className="list-disc pl-5 text-gray-600">
              <li>Pending: {pullRequestStatuses.pending}</li>
              <li>Approved: {pullRequestStatuses.approved}</li>
              <li>Rejected: {pullRequestStatuses.rejected}</li>
            </ul>
          </div>
        </section>

        <h2 className="text-xl font-semibold mb-4">Your Pull Requests</h2>
        <div className="mb-4">
          <label htmlFor="project-select" className="mr-2">Filter by Project:</label>
          <select
            id="project-select"
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="p-2 border rounded"
          >
            <option value="">All Projects</option>
            {projects.map((project) => (
              <option key={project} value={project}>
                {project}
              </option>
            ))}
          </select>
        </div>
        {userPullRequests.map((pr) => (
          <div key={`${pr.pullRequestId}-${pr.projectName}`} className="border p-4 rounded mb-4 bg-gray-50 hover:shadow transition">
            <div className="flex justify-between mb-2">
              <strong>PR #{pr.pullRequestId}</strong>
              <span className={`text-sm ${pr.status === "approved" ? "text-green-600" : pr.status === "rejected" ? "text-red-600" : "text-yellow-600"}`}>
                Status: {pr.status}
              </span>
            </div>
            <p className="text-sm text-gray-700">
              Project: {pr.projectName} • {fmt(pr.timestamp)}
            </p>
          </div>
        ))}

        {userPullRequests.length === 0 && (
          <p className="text-gray-500 text-center py-8">No pull requests found.</p>
        )}
        <p className="mt-6 text-sm">{status}</p>
      </main>
    </div>
  );
}

export default DeveloperDashboard;