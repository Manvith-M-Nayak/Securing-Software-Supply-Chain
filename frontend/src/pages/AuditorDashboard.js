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
    <>
      <div className="container">
        <div className="header">
          <h1>Auditor Dashboard</h1>
          <button onClick={onLogout} className="logout-btn">Logout</button>
        </div>

        <div className="actions">
          <select
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
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
            disabled={!canViewProject || !projectName}
            className={!canViewProject || !projectName ? 'btn-disabled' : ''}
          >
            Refresh
          </button>
        </div>

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading...</p>
          </div>
        )}

        {error && (
          <p className="error">{error}</p>
        )}

        {!loading && !canViewProject && projectName && (
          <p className="error">Unauthorized project</p>
        )}

        {!loading && pullRequests.length === 0 && projectName && (
          <p className="info">No pending pull requests</p>
        )}

        <div className="pr-list">
          {pullRequests.map((pr) => (
            <div key={pr.pullRequestId} className="pr-item">
              <div className="pr-grid">
                <div>
                  <p><strong>PR ID:</strong> {pr.pullRequestId}</p>
                  <p><strong>Project:</strong> {pr.projectName}</p>
                  <p><strong>Version:</strong> {pr.version}</p>
                </div>
                <div>
                  <p><strong>Developer:</strong> {pr.developer}</p>
                  <p><strong>Timestamp:</strong> {new Date(pr.timestamp).toLocaleString()}</p>
                </div>
              </div>

              <p className="file-title">Changed Files:</p>
              <div className="file-container">
                {pr.changedFiles.map((file, index) => (
                  <div key={index} className="file-item">
                    <p className="filename">{file.filename}</p>
                    <pre>{file.content}</pre>
                    <p>
                      <strong>Vulnerability Status:</strong>{' '}
                      <span className={file.vulnerability.is_vulnerable ? 'text-red' : 'text-green'}>
                        {file.vulnerability.is_vulnerable ? 'Vulnerable' : 'Safe'}
                      </span>
                    </p>
                    {file.vulnerability.is_vulnerable && (
                      <div className="vuln-details">
                        <p>Vulnerability Details:</p>
                        <ul className="vuln-list">
                          {Array.isArray(file.vulnerability.details) ? (
                            file.vulnerability.details.map((vuln, idx) => (
                              <li key={idx}>
                                <strong>{vuln.type}</strong> at line {vuln.line}:{' '}
                                <pre className="vuln-snippet">{vuln.snippet}</pre>
                              </li>
                            ))
                          ) : (
                            <li>{file.vulnerability.details}</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="decision-buttons">
                <button
                  onClick={() => handleDecision(pr.pullRequestId, 'approve')}
                  className="approve-btn"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleDecision(pr.pullRequestId, 'reject')}
                  className="reject-btn"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
      <style jsx>{`
        .container {
          font-family: 'Arial', sans-serif;
          background-color: #f4f6f9;
          min-height: 100vh;
          padding: 24px;
          margin: 0 auto;
          max-width: 1280px;
          color: #333;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 32px;
        }
        h1 {
          font-size: 1.875rem;
          font-weight: bold;
          color: #1e3a8a;
        }
        .logout-btn {
          padding: 8px 24px;
          background-color: #ef4444;
          color: #fff;
          border: none;
          border-radius: 6px;
          font-size: 1rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        .logout-btn:hover {
          background-color: #b91c1c;
        }
        .actions {
          display: flex;
          gap: 16px;
          margin-bottom: 32px;
          align-items: center;
        }
        select {
          padding: 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background-color: #fff;
          font-size: 1rem;
          flex: 1;
          cursor: pointer;
        }
        select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        button {
          padding: 12px 24px;
          background-color: #3b82f6;
          color: #fff;
          border: none;
          border-radius: 6px;
          font-size: 1rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        button:hover {
          background-color: #1e3a8a;
        }
        .btn-disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
        }
        .btn-disabled:hover {
          background-color: #9ca3af;
        }
        .loading {
          text-align: center;
        }
        .spinner {
          display: inline-block;
          width: 32px;
          height: 32px;
          border: 2px solid #3b82f6;
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 8px;
        }
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
        .loading p {
          color: #4b5563;
          font-size: 1rem;
        }
        .error {
          background-color: #fee2e2;
          color: #b91c1c;
          padding: 16px;
          border-radius: 6px;
          margin-bottom: 24px;
          text-align: center;
          font-size: 1rem;
        }
        .info {
          background-color: #dbeafe;
          color: #1e40af;
          padding: 16px;
          border-radius: 6px;
          margin-bottom: 24px;
          text-align: center;
          font-size: 1rem;
        }
        .pr-list {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .pr-item {
          background-color: #fff;
          padding: 24px;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          transition: box-shadow 0.2s;
        }
        .pr-item:hover {
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
        .pr-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 16px;
          margin-bottom: 16px;
        }
        @media (min-width: 768px) {
          .pr-grid {
            grid-template-columns: 1fr 1fr;
          }
        }
        .pr-grid p {
          color: #4b5563;
          margin: 4px 0;
        }
        .pr-grid p strong {
          color: #1f2937;
        }
        .file-title {
          font-size: 1.125rem;
          color: #1f2937;
          font-weight: 500;
          margin-bottom: 8px;
        }
        .file-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .file-item {
          border-left: 4px solid #e5e7eb;
          padding-left: 16px;
        }
        .filename {
          font-size: 1rem;
          font-weight: 500;
          color: #1f2937;
          margin-bottom: 8px;
        }
        pre {
          background-color: #f9fafb;
          padding: 16px;
          border-radius: 6px;
          font-size: 0.875rem;
          color: #374151;
          overflow-x: auto;
          white-space: pre-wrap;
        }
        .file-item p {
          margin-top: 8px;
        }
        .file-item p strong {
          color: #1f2937;
        }
        .text-red {
          color: #b91c1c;
        }
        .text-green {
          color: #10b981;
        }
        .vuln-details {
          margin-top: 8px;
        }
        .vuln-details p {
          color: #1f2937;
          font-weight: 500;
        }
        .vuln-list {
          list-style: disc;
          padding-left: 24px;
          margin-top: 8px;
          color: #4b5563;
        }
        .vuln-list li strong {
          color: #1f2937;
        }
        .vuln-snippet {
          display: inline-block;
          background-color: #f9fafb;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.875rem;
        }
        .decision-buttons {
          display: flex;
          gap: 16px;
          margin-top: 24px;
        }
        .approve-btn {
          background-color: #10b981;
        }
        .approve-btn:hover {
          background-color: #059669;
        }
        .reject-btn {
          background-color: #ef4444;
        }
        .reject-btn:hover {
          background-color: #b91c1c;
        }
        @media (max-width: 768px) {
          .container {
            padding: 16px;
          }
          h1 {
            font-size: 1.5rem;
          }
          .header {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }
          .actions {
            flex-direction: column;
            align-items: stretch;
          }
          select, button {
            width: 100%;
          }
          .decision-buttons {
            flex-direction: column;
          }
        }
      `}</style>
    </>
  );
};

export default AuditorDashboard;