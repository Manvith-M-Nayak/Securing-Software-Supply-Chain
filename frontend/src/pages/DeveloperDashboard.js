import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001';

// Custom debounce hook
const useDebounce = (callback, delay) => {
  const timeoutRef = useRef(null);
  return useCallback((...args) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  }, [callback, delay]);
};

const DeveloperDashboard = () => {
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [leaderboard, setLeaderboard] = useState([]);
  const hasFetchedProjects = useRef(false);
  const lastFetchedProject = useRef(null);
  const isMounted = useRef(false);

  // Validate ObjectId
  const ObjectId = {
    isValid: (id) => /^[0-9a-fA-F]{24}$/.test(id)
  };

  // Memoize user to prevent re-renders
  const memoizedUser = useMemo(() => user, [user]);

  // Load user from localStorage
  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem('user'));
      if (u && u.id && u.username && ObjectId.isValid(u.id) && u.role === 'developer') {
        setUser(u);
        setLoading(false);
      } else {
        setError('User not logged in or invalid user data. Please log in again.');
        window.location.href = '/login';
      }
    } catch (err) {
      console.error('User load failed:', err);
      setError('Failed to load user. Please log in again.');
      window.location.href = '/login';
    }
  }, []);

  // Initialize selectedProject from localStorage
  useEffect(() => {
    if (projects.length > 0) {
      const storedProject = localStorage.getItem('selectedProject');
      if (storedProject && projects.includes(storedProject)) {
        setSelectedProject(storedProject);
      } else if (!selectedProject && projects.length > 0) {
        setSelectedProject(projects[0]);
      }
    }
  }, [projects, selectedProject]);

  // Persist selectedProject to localStorage
  useEffect(() => {
    if (selectedProject && projects.includes(selectedProject)) {
      localStorage.setItem('selectedProject', selectedProject);
    }
  }, [selectedProject, projects]);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    if (!memoizedUser?.id || hasFetchedProjects.current) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/dev/user_projects/${memoizedUser.id}`, {
        headers: { 'X-User-Email': memoizedUser.email }
      });
      const projectNames = response.data.projects
        .map(p => p.projectName || p.name)
        .filter(p => p && typeof p === 'string' && p.trim())
        .filter((v, i, a) => a.indexOf(v) === i);
      setProjects(projectNames);
      hasFetchedProjects.current = true;
      // Update user data with points
      const updatedUser = {
        ...memoizedUser,
        points: response.data.projects.reduce((acc, p) => {
          acc[p.projectName || p.name] = response.data.points?.[p.projectName || p.name] || 0;
          return acc;
        }, {})
      };
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      console.log('Fetched projects and updated user points:', updatedUser.points);
      if (projectNames.length === 0) {
        setError('No projects assigned to this user.');
      }
    } catch (err) {
      setError(`Failed to fetch projects: ${err.response?.data?.error || err.message}`);
      console.error('Project fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [memoizedUser]);

  // Fetch pull requests
  const fetchPullRequests = useCallback(async () => {
    if (!memoizedUser || !selectedProject || !projects.includes(selectedProject)) {
      console.log('Skipping fetchPullRequests: missing user or invalid project', {
        hasUser: !!memoizedUser,
        selectedProject,
        isProjectValid: projects.includes(selectedProject)
      });
      return;
    }
    setLoading(true);
    const url = `${API_BASE_URL}/dev/pullrequests?project=${selectedProject}`;
    console.log('Fetching pull requests:', { url, email: memoizedUser.email });
    try {
      const response = await axios.get(url, {
        headers: { 'X-User-Email': memoizedUser.email }
      });
      const uniquePullRequests = Array.from(
        new Map(response.data.pullrequests.map(pr => [JSON.stringify([pr.pullRequestId, pr.projectName]), pr])).values()
      );
      setPullRequests(uniquePullRequests);
      // Update user points from response
      if (response.data.points !== undefined) {
        const updatedUser = {
          ...memoizedUser,
          points: { ...memoizedUser.points, [selectedProject]: response.data.points }
        };
        setUser(updatedUser);
        localStorage.setItem('user', JSON.stringify(updatedUser));
        console.log(`Updated points for ${selectedProject}: ${response.data.points}`);
      }
      console.log(`Fetched ${uniquePullRequests.length} pull requests for project ${selectedProject}`);
    } catch (err) {
      const errorMessage = `Failed to fetch pull requests: ${err.message} (Status: ${err.response?.status || 'N/A'})`;
      setError(errorMessage);
      console.error('Pull request fetch error:', {
        message: err.message,
        code: err.code,
        response: err.response?.data,
        status: err.response?.status
      });
    } finally {
      setLoading(false);
    }
  }, [memoizedUser, selectedProject, projects]);

  // Fetch leaderboard
  const fetchLeaderboard = useCallback(async () => {
    if (!memoizedUser || !selectedProject || !projects.includes(selectedProject)) {
      console.log('Skipping fetchLeaderboard: missing user or invalid project');
      return;
    }
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/dev/leaderboard?project=${selectedProject}`, {
        headers: { 'X-User-Email': memoizedUser.email }
      });
      setLeaderboard(response.data.developers || []);
      setError(null);
      console.log(`Fetched leaderboard for project ${selectedProject}`);
    } catch (err) {
      setError(`Failed to fetch leaderboard: ${err.response?.data?.error || err.message}`);
      console.error('Leaderboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [memoizedUser, selectedProject, projects]);

  // Debounced fetch functions
  const debouncedFetchPullRequests = useDebounce(fetchPullRequests, 1000);
  const debouncedFetchLeaderboard = useDebounce(fetchLeaderboard, 1000);

  // Fetch projects on mount
  useEffect(() => {
    if (memoizedUser && !hasFetchedProjects.current) {
      fetchProjects();
    }
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, [memoizedUser, fetchProjects]);

  // Fetch pull requests and leaderboard when selectedProject changes
  useEffect(() => {
    if (selectedProject && projects.includes(selectedProject)) {
      console.log(`Selected project changed to: ${selectedProject}, triggering fetch`);
      debouncedFetchPullRequests();
      debouncedFetchLeaderboard();
    }
  }, [selectedProject, projects, debouncedFetchPullRequests, debouncedFetchLeaderboard]);

  const handleLogout = () => {
    localStorage.removeItem('selectedProject');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  const handleRefresh = () => {
    if (selectedProject && projects.includes(selectedProject)) {
      lastFetchedProject.current = null; // Allow re-fetch on manual refresh
      debouncedFetchPullRequests();
      debouncedFetchLeaderboard();
    }
  };

  const fmt = (t) => new Date(t).toLocaleString();

  // Truncate transaction hash for display
  const truncateHash = (hash) => {
    if (!hash || hash === 'N/A' || hash === 'Failed') return hash;
    return `${hash.slice(0, 5)}...${hash.slice(-5)}`;
  };

  return (
    <>
      <div className="container">
        <div className="header">
          <h1>Developer Dashboard</h1>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
        {memoizedUser && (
          <div className="user-info">
            <p>Logged in as: {memoizedUser.username}</p>
            <p className="points">Points: {memoizedUser.points?.[selectedProject] || 0} ({selectedProject || 'No project selected'})</p>
          </div>
        )}
        <div className="actions">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
          >
            <option value="">Select Project</option>
            {projects.map((project) => (
              <option key={project} value={project}>
                {project}
              </option>
            ))}
          </select>
          <button
            onClick={handleRefresh}
            disabled={!selectedProject}
          >
            Refresh
          </button>
        </div>

        {loading && <p className="loading">Loading...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !selectedProject && <p className="error">Please select a project</p>}
        {!loading && pullRequests.length === 0 && selectedProject && <p className="error">No pull requests found</p>}

        <div className="table-container">
          <h2>Leaderboard ({selectedProject || 'Select a project'})</h2>
          {leaderboard.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Username</th>
                  <th>GitHub</th>
                  <th>Points</th>
                  <th>Project</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((dev, index) => (
                  <tr key={dev._id}>
                    <td>{index + 1}</td>
                    <td>{dev.username}</td>
                    <td>{dev.githubUsername}</td>
                    <td>{dev.points || 0}</td>
                    <td>{selectedProject}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No developers found for this project.</p>
          )}
        </div>

        <ul className="pr-list">
          {pullRequests.map((pr) => (
            <li key={`${pr.pullRequestId}-${pr.projectName}`} className="pr-item">
              <div className="pr-header">
                <strong>PR #{pr.pullRequestId}</strong>
                <span
                  className={`pr-status-${
                    pr.status === 'approved' ? 'approved' :
                    pr.status === 'rejected' ? 'rejected' : 'pending'
                  }`}
                >
                  Status: {pr.status}
                </span>
              </div>
              <div className="pr-details">
                <p><strong>Project:</strong> {pr.projectName}</p>
                <p><strong>Version:</strong> {pr.version}</p>
                <p><strong>Timestamp:</strong> {fmt(pr.timestamp)}</p>
                <p><strong>Transaction Hash:</strong> <span title={pr.txHash}>{truncateHash(pr.txHash)}</span></p>
                <p><strong>Changed Files:</strong></p>
                <ul className="file-list">
                  {pr.changedFiles.map((file, index) => (
                    <li key={index} className="file-item">
                      <strong>{file.filename}</strong>
                      <pre>{file.content}</pre>
                      <p><strong>Vulnerability Status:</strong> {file.vulnerability.is_vulnerable ? 'Vulnerable' : 'Safe'}</p>
                      {file.vulnerability.is_vulnerable && (
                        <div className="vuln-details">
                          <p><strong>Vulnerability Details:</strong></p>
                          <ul className="vuln-list">
                            {Array.isArray(file.vulnerability.details) ? (
                              file.vulnerability.details.map((vuln, idx) => (
                                <li key={idx}>
                                  <strong>{vuln.type}</strong> at line {vuln.line}: <pre>{vuln.snippet}</pre>
                                </li>
                              ))
                            ) : (
                              <li>{file.vulnerability.details}</li>
                            )}
                          </ul>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ul>
      </div>
      <style jsx>{`
        .container {
          font-family: 'Arial', sans-serif;
          background-color: #f4f6f9;
          margin: 0 auto;
          padding: 20px;
          max-width: 1200px;
          color: #333;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        h1 {
          font-size: 2rem;
          color: #1e3a8a;
          margin: 0;
        }
        .logout-btn {
          padding: 0.75rem 1.5rem;
          background-color: #ef4444;
          color: #fff;
          border: none;
          border-radius: 5px;
          font-size: 1rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        .logout-btn:hover {
          background-color: #b91c1c;
        }
        .user-info {
          background-color: #fff;
          padding: 1rem;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          margin-bottom: 1.5rem;
        }
        .user-info p {
          margin: 0.5rem 0;
          font-size: 1.1rem;
        }
        .user-info .points {
          color: #4b5563;
          font-size: 1rem;
        }
        .actions {
          display: flex;
          gap: 1rem;
          margin-bottom: 1.5rem;
          align-items: center;
        }
        select, button {
          padding: 0.75rem;
          border-radius: 5px;
          font-size: 1rem;
          cursor: pointer;
        }
        select {
          border: 1px solid #d1d5db;
          background-color: #fff;
          flex: 1;
        }
        select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        button {
          background-color: #3b82f6;
          color: #fff;
          border: none;
          transition: background-color 0.2s;
        }
        button:hover {
          background-color: #1e3a8a;
        }
        button:disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
        }
        .error {
          color: #ef4444;
          font-size: 1rem;
          margin-bottom: 1rem;
          text-align: center;
        }
        .loading {
          color: #4b5563;
          text-align: center;
          font-size: 1rem;
        }
        .table-container {
          background-color: #fff;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          overflow-x: auto;
          margin-bottom: 2rem;
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        th, td {
          padding: 0.75rem;
          text-align: left;
          border-bottom: 1px solid #e5e7eb;
        }
        th {
          background-color: #f9fafb;
          font-weight: 600;
          color: #1e3a8a;
        }
        tr:nth-child(even) {
          background-color: #f9fafb;
        }
        .pr-list {
          list-style: none;
          padding: 0;
        }
        .pr-item {
          background-color: #fff;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 1rem;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .pr-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }
        .pr-status-approved {
          color: #10b981;
          font-weight: 500;
        }
        .pr-status-rejected {
          color: #ef4444;
          font-weight: 500;
        }
        .pr-status-pending {
          color: #f59e0b;
          font-weight: 500;
        }
        .pr-details p {
          margin: 0.5rem 0;
        }
        .file-list {
          list-style: disc;
          padding-left: 1.5rem;
          margin-top: 0.5rem;
        }
        .file-item pre {
          background-color: #f9fafb;
          padding: 0.75rem;
          border-radius: 5px;
          overflow-x: auto;
          font-size: 0.9rem;
        }
        .vuln-details {
          margin-top: 0.5rem;
        }
        .vuln-list {
          list-style: disc;
          padding-left: 1.5rem;
        }
        @media (max-width: 768px) {
          .container {
            padding: 10px;
          }
          h1 {
            font-size: 1.5rem;
          }
          .header {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
          .logout-btn {
            align-self: flex-end;
          }
          h2 {
            font-size: 1.25rem;
          }
          .actions {
            flex-direction: column;
            align-items: stretch;
          }
          select, button {
            width: 100%;
          }
        }
      `}</style>
    </>
  );
};

export default DeveloperDashboard;
