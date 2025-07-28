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
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Developer Dashboard</h1>
      {memoizedUser && (
        <div className="mb-4">
          <p className="text-lg font-semibold">Logged in as: {memoizedUser.username}</p>
          <p className="text-gray-600">Points: {memoizedUser.points?.[selectedProject] || 0} ({selectedProject || 'No project selected'})</p>
        </div>
      )}
      <button onClick={handleLogout} className="mb-4 px-4 py-2 bg-red-500 text-white rounded">
        Logout
      </button>

      <div className="mb-4">
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="border p-2 rounded mr-2"
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
          className="px-4 py-2 bg-blue-500 text-white rounded"
          disabled={!selectedProject}
        >
          Refresh
        </button>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {!loading && !selectedProject && <p className="text-red-500">Please select a project</p>}
      {!loading && pullRequests.length === 0 && selectedProject && <p>No pull requests found</p>}

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Leaderboard ({selectedProject || 'Select a project'})</h2>
        {leaderboard.length > 0 ? (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 p-3 text-left">Rank</th>
                <th className="border border-gray-300 p-3 text-left">Username</th>
                <th className="border border-gray-300 p-3 text-left">GitHub</th>
                <th className="border border-gray-300 p-3 text-left">Points</th>
                <th className="border border-gray-300 p-3 text-left">Project</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((dev, index) => (
                <tr key={dev._id} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                  <td className="border border-gray-300 p-3">{index + 1}</td>
                  <td className="border border-gray-300 p-3">{dev.username}</td>
                  <td className="border border-gray-300 p-3">{dev.githubUsername}</td>
                  <td className="border border-gray-300 p-3">{dev.points || 0}</td>
                  <td className="border border-gray-300 p-3">{selectedProject}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">No developers found for this project.</p>
        )}
      </div>

      <ul className="space-y-4">
        {pullRequests.map((pr) => (
          <li key={`${pr.pullRequestId}-${pr.projectName}`} className="border p-4 rounded">
            <div className="flex justify-between mb-2">
              <strong>PR #{pr.pullRequestId}</strong>
              <span
                className={`text-sm font-medium ${
                  pr.status === 'approved' ? 'text-green-600' :
                  pr.status === 'rejected' ? 'text-red-600' : 'text-yellow-600'
                }`}
              >
                Status: {pr.status}
              </span>
            </div>
            <p><strong>Project:</strong> {pr.projectName}</p>
            <p><strong>Version:</strong> {pr.version}</p>
            <p><strong>Timestamp:</strong> {fmt(pr.timestamp)}</p>
            <p><strong>Transaction Hash:</strong> <span title={pr.txHash}>{truncateHash(pr.txHash)}</span></p>
            <p><strong>Changed Files:</strong></p>
            <ul className="list-disc pl-5">
              {pr.changedFiles.map((file, index) => (
                <li key={index}>
                  <strong>{file.filename}</strong>
                  <pre>{file.content}</pre>
                  <p><strong>Vulnerability Status:</strong> {file.vulnerability.is_vulnerable ? 'Vulnerable' : 'Safe'}</p>
                  {file.vulnerability.is_vulnerable && (
                    <div>
                      <p><strong>Vulnerability Details:</strong></p>
                      <ul className="list-disc pl-5">
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
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DeveloperDashboard;