import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuditorDashboard = ({ user, onLogout }) => {
  const [pullRequests, setPullRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [projectName, setProjectName] = useState('');

  const fetchPullRequests = useCallback(async () => {
    if (!projectName) return;
    setLoading(true);
    try {
      console.log('Fetching pull requests for projectName:', projectName, 'with email:', user.email);
      const response = await axios.get(`http://localhost:5001/auditor/dashboard?projectName=${projectName}`, {
        headers: { 'X-User-Email': user.email }
      });
      setPullRequests(response.data.pullRequests || []);
      setError(null);
    } catch (err) {
      const errorMessage = `Failed to fetch pull requests: ${err.message} (Status: ${err.response?.status || 'N/A'})`;
      setError(errorMessage);
      console.error('Error details:', {
        message: err.message,
        code: err.code,
        response: err.response?.data,
        status: err.response?.status,
        headers: err.response?.headers,
      });
    } finally {
      setLoading(false);
    }
  }, [projectName, user.email]);

  useEffect(() => {
    if (projectName) {
      fetchPullRequests();
    } else {
      setPullRequests([]);
      setLoading(false);
    }
  }, [projectName, fetchPullRequests]);

  const handleDecision = async (pullRequestId, decision) => {
    try {
      await axios.post('http://localhost:5001/auditor/decision', {
        pullRequestId,
        decision,
        projectName
      }, {
        headers: { 'X-User-Email': user.email }
      });
      fetchPullRequests();
    } catch (err) {
      const errorMessage = `Failed to process decision: ${err.message}`;
      setError(errorMessage);
      console.error('Decision error details:', {
        message: err.message,
        code: err.code,
        response: err.response?.data,
        status: err.response?.status,
      });
    }
  };

  const assignedProjects = user.assignedProjects || [];
  const canViewProject = assignedProjects.some(p => p.projectName === projectName);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">Auditor Dashboard</h1>
          <button 
            onClick={onLogout} 
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors duration-200"
          >
            Logout
          </button>
        </div>
        
        <div className="mb-8 flex gap-4">
          <select
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="flex-1 p-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            className={`px-6 py-3 rounded-lg text-white font-medium ${
              !canViewProject || !projectName 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            } transition-colors duration-200`}
            disabled={!canViewProject || !projectName}
          >
            Refresh
          </button>
        </div>

        {loading && (
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-2 text-gray-600">Loading...</p>
          </div>
        )}
        
        {error && (
          <p className="p-4 bg-red-100 text-red-700 rounded-lg mb-6">{error}</p>
        )}
        
        {!loading && !canViewProject && projectName && (
          <p className="p-4 bg-red-100 text-red-700 rounded-lg mb-6">Unauthorized project</p>
        )}
        
        {!loading && pullRequests.length === 0 && projectName && (
          <p className="p-4 bg-blue-100 text-blue-700 rounded-lg mb-6">No pending pull requests</p>
        )}

        <div className="space-y-6">
          {pullRequests.map((pr) => (
            <div 
              key={pr.pullRequestId} 
              className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-gray-600"><strong className="text-gray-800">PR ID:</strong> {pr.pullRequestId}</p>
                  <p className="text-gray-600"><strong className="text-gray-800">Project:</strong> {pr.projectName}</p>
                  <p className="text-gray-600"><strong className="text-gray-800">Version:</strong> {pr.version}</p>
                </div>
                <div>
                  <p className="text-gray-600"><strong className="text-gray-800">Developer:</strong> {pr.developer}</p>
                  <p className="text-gray-600"><strong className="text-gray-800">Timestamp:</strong> {new Date(pr.timestamp).toLocaleString()}</p>
                </div>
              </div>

              <p className="text-gray-800 font-medium mb-2">Changed Files:</p>
              <div className="space-y-4">
                {pr.changedFiles.map((file, index) => (
                  <div key={index} className="border-l-4 border-gray-200 pl-4">
                    <p className="text-gray-800 font-medium">{file.filename}</p>
                    <pre className="bg-gray-50 p-4 rounded-lg text-sm text-gray-700 overflow-x-auto">
                      {file.content}
                    </pre>
                    <p className="mt-2">
                      <strong className="text-gray-800">Vulnerability Status:</strong>{' '}
                      <span className={file.vulnerability.is_vulnerable ? 'text-red-600' : 'text-green-600'}>
                        {file.vulnerability.is_vulnerable ? 'Vulnerable' : 'Safe'}
                      </span>
                    </p>
                    {file.vulnerability.is_vulnerable && (
                      <div className="mt-2">
                        <p className="text-gray-800 font-medium">Vulnerability Details:</p>
                        <ul className="list-disc pl-6 mt-2 space-y-2">
                          {Array.isArray(file.vulnerability.details) ? (
                            file.vulnerability.details.map((vuln, idx) => (
                              <li key={idx} className="text-gray-600">
                                <strong className="text-gray-800">{vuln.type}</strong> at line {vuln.line}:{' '}
                                <pre className="inline-block bg-gray-50 p-2 rounded text-sm">{vuln.snippet}</pre>
                              </li>
                            ))
                          ) : (
                            <li className="text-gray-600">{file.vulnerability.details}</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-6 flex gap-4">
                <button
                  onClick={() => handleDecision(pr.pullRequestId, 'approve')}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors duration-200"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleDecision(pr.pullRequestId, 'reject')}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors duration-200"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AuditorDashboard;