import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AuditorDashboard = ({ user, onLogout }) => {
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [projectName, setProjectName] = useState('');

  useEffect(() => {
    if (projectName) {
      fetchPullRequests();
    } else {
      setPullRequests([]);
      setLoading(false);
    }
  }, [projectName]);

  const fetchPullRequests = async () => {
    setLoading(true);
    try {
      console.log('Fetching pull requests for projectName:', projectName, 'with email:', user.email);
      const response = await axios.get(`http://localhost:5001/auditor/dashboard?projectName=${projectName}`, {
        headers: { 'X-User-Email': user.email }
      });
      setPullRequests(response.data.pullRequests || []);
      setError(null);
    } catch (err) {
      setError(`Failed to fetch pull requests: ${err.message} (Status: ${err.response?.status})`);
      console.error('Error fetching pull requests:', err.response?.data || err);
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (pullRequestId, decision) => {
    try {
      await axios.post('http://localhost:5001/auditor/decision', {
        pullRequestId,
        decision
      }, {
        headers: { 'X-User-Email': user.email }
      });
      fetchPullRequests();
    } catch (err) {
      setError(`Failed to process decision: ${err.message}`);
      console.error('Error processing decision:', err.response?.data || err);
    }
  };

  const assignedProjects = user.assignedProjects || [];
  const canViewProject = assignedProjects.some(p => p.projectName === projectName);

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Auditor Dashboard</h1>
      <button onClick={onLogout} className="mb-4 px-4 py-2 bg-red-500 text-white rounded">
        Logout
      </button>
      <div className="mb-4">
        <select
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          className="border p-2 rounded mr-2"
        >
          <option value="">Select Project</option>
          {assignedProjects.map(p => (
            <option key={p.projectName} value={p.projectName}>
              {p.projectName}
            </option>
          ))}
        </select>
        <button
          onClick={fetchPullRequests}
          className="px-4 py-2 bg-blue-500 text-white rounded"
          disabled={!canViewProject || !projectName}
        >
          Refresh
        </button>
      </div>
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {!loading && !canViewProject && projectName && <p className="text-red-500">Unauthorized project</p>}
      {!loading && pullRequests.length === 0 && projectName && <p>No pending pull requests</p>}
      <ul className="space-y-4">
        {pullRequests.map((pr) => (
          <li key={pr.pullRequestId} className="border p-4 rounded">
            <p><strong>PR ID:</strong> {pr.pullRequestId}</p>
            <p><strong>Project:</strong> {pr.projectName}</p>
            <p><strong>Version:</strong> {pr.version}</p>
            <p><strong>Developer:</strong> {pr.developer}</p>
            <p><strong>Timestamp:</strong> {new Date(pr.timestamp).toLocaleString()}</p>
            <p><strong>Security Score:</strong> {pr.securityScore || 'N/A'}</p>
            <p><strong>Changed Files:</strong></p>
            <ul className="list-disc pl-5">
              {pr.changedFiles.map((file, index) => (
                <li key={index}>
                  <strong>{file.filename}</strong>: <pre>{file.content}</pre>
                </li>
              ))}
            </ul>
            <div className="mt-2">
              <button
                onClick={() => handleDecision(pr.pullRequestId, 'approve')}
                className="px-4 py-2 bg-green-500 text-white rounded mr-2"
              >
                Approve
              </button>
              <button
                onClick={() => handleDecision(pr.pullRequestId, 'reject')}
                className="px-4 py-2 bg-red-500 text-white rounded"
              >
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AuditorDashboard;