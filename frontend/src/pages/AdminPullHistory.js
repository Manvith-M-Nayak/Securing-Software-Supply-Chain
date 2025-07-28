import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001';

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '1.5rem',
    backgroundColor: '#f7fafc',
    minHeight: '100vh',
  },
  title: {
    fontSize: '1.875rem',
    fontWeight: '700',
    color: '#1a202c',
    marginBottom: '1.5rem',
  },
  error: {
    backgroundColor: '#fed7d7',
    color: '#742a2a',
    padding: '1rem',
    borderRadius: '0.5rem',
    marginBottom: '1.5rem',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  flexContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    marginBottom: '1.5rem',
    '@media (min-width: 640px)': {
      flexDirection: 'row',
    },
  },
  selectContainer: {
    flex: '1',
  },
  label: {
    display: 'block',
    color: '#4a5568',
    fontWeight: '500',
    marginBottom: '0.5rem',
  },
  select: {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #e2e8f0',
    borderRadius: '0.5rem',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    ':focus': {
      borderColor: '#3182ce',
      boxShadow: '0 0 0 2px rgba(49, 130, 206, 0.5)',
    },
    ':disabled': {
      backgroundColor: '#edf2f7',
      cursor: 'not-allowed',
    },
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#718096',
  },
  spinner: {
    animation: 'spin 1s linear infinite',
    height: '1.25rem',
    width: '1.25rem',
    marginRight: '0.5rem',
    color: '#3182ce',
  },
  tableContainer: {
    overflowX: 'auto',
    backgroundColor: '#ffffff',
    borderRadius: '0.5rem',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  thead: {
    backgroundColor: '#edf2f7',
  },
  th: {
    padding: '0.75rem 1.5rem',
    textAlign: 'left',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#4a5568',
    borderBottom: '1px solid #e2e8f0',
  },
  tbody: {
    borderTop: '1px solid #e2e8f0',
  },
  tr: {
    transition: 'background-color 0.2s',
    ':hover': {
      backgroundColor: '#f7fafc',
    },
  },
  td: {
    padding: '1rem 1.5rem',
    fontSize: '0.875rem',
    color: '#4a5568',
    borderBottom: '1px solid #e2e8f0',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '0.25rem 0.5rem',
    borderRadius: '9999px',
    fontSize: '0.75rem',
    fontWeight: '500',
  },
  statusPending: {
    backgroundColor: '#fefcbf',
    color: '#744210',
  },
  statusApproved: {
    backgroundColor: '#c6f6d5',
    color: '#2f855a',
  },
  statusRejected: {
    backgroundColor: '#fed7d7',
    color: '#c53030',
  },
  link: {
    color: '#2b6cb0',
    textDecoration: 'none',
    ':hover': {
      color: '#2c5282',
      textDecoration: 'underline',
    },
  },
  noData: {
    textAlign: 'center',
    padding: '1rem',
    color: '#718096',
  },
};

const AdminPullHistory = ({ githubUsername: propGithubUsername, email: propEmail }) => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [pullRequests, setPullRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [githubUsername, setGithubUsername] = useState(propGithubUsername || '');
  const [userEmail, setUserEmail] = useState(propEmail || '');

  useEffect(() => {
    if (!propGithubUsername || !propEmail) {
      console.log('Missing githubUsername or email props, checking localStorage');
      const stored = localStorage.getItem('user');
      if (stored) {
        try {
          const parsedUser = JSON.parse(stored);
          console.log('Parsed user from localStorage:', parsedUser);
          if (
            parsedUser.githubUsername &&
            typeof parsedUser.githubUsername === 'string' &&
            parsedUser.githubUsername.trim() &&
            parsedUser.email &&
            typeof parsedUser.email === 'string' &&
            parsedUser.email.trim() &&
            parsedUser.role === 'admin'
          ) {
            setGithubUsername(parsedUser.githubUsername);
            setUserEmail(parsedUser.email);
            console.log('Set githubUsername from localStorage:', parsedUser.githubUsername);
            console.log('Set userEmail from localStorage:', parsedUser.email);
          } else {
            console.error('Invalid user data in localStorage:', parsedUser);
            setError('Invalid user data or not an admin. Please log in again.');
            window.location.href = '/login';
          }
        } catch (e) {
          console.error('Failed to parse user from localStorage:', e);
          setError('Failed to parse user data. Please log in again.');
          window.location.href = '/login';
        }
      } else {
        console.error('No user data found in localStorage');
        setError('No user data found. Please log in.');
        window.location.href = '/login';
      }
    } else {
      console.log('Using githubUsername from props:', propGithubUsername);
      console.log('Using email from props:', propEmail);
      setGithubUsername(propGithubUsername);
      setUserEmail(propEmail);
    }
  }, [propGithubUsername, propEmail]);

  const fetchProjects = useCallback(async () => {
    if (!githubUsername || typeof githubUsername !== 'string' || !githubUsername.trim()) {
      console.error('Invalid or missing githubUsername:', githubUsername);
      setError('Invalid or missing GitHub username');
      setProjects([]);
      return;
    }
    try {
      setLoading(true);
      const url = `${API_BASE_URL}/admin/projects/${encodeURIComponent(githubUsername)}`;
      console.log(`Fetching projects from: ${url}`);
      const response = await axios.get(url, {
        headers: { 'X-User-Email': userEmail }
      });
      console.log('Raw projects response:', response);
      console.log('Projects data:', response.data);
      const fetchedProjects = response.data.projects || [];
      if (!Array.isArray(fetchedProjects)) {
        console.error('Projects response is not an array:', fetchedProjects);
        setError('Invalid projects response format: not an array');
        setProjects([]);
        return;
      }
      console.log('Fetched projects:', fetchedProjects);
      const validProjects = fetchedProjects.filter(
        p => p && p.name && typeof p.name === 'string' && p.name.trim()
      );
      console.log('Valid projects after filtering:', validProjects);
      if (validProjects.length === 0 && fetchedProjects.length > 0) {
        console.warn('No valid projects after filtering, raw projects:', fetchedProjects);
        setError('No valid projects found (missing or invalid name fields)');
        setProjects(fetchedProjects.map(p => ({
          ...p,
          name: p.name || p._id || 'Unnamed Project'
        })));
      } else {
        setProjects(validProjects);
      }
      if (validProjects.length > 0) {
        setSelectedProject(validProjects[0].name);
        console.log('Set selected project:', validProjects[0].name);
      } else if (fetchedProjects.length === 0) {
        setError('No projects found for this admin');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message;
      console.error('Error fetching projects:', err);
      console.error('Error details:', {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message
      });
      setError(`Failed to fetch projects: ${errorMessage}`);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [githubUsername, userEmail]);

  useEffect(() => {
    if (githubUsername && userEmail) {
      console.log('Triggering fetchProjects with githubUsername:', githubUsername, 'and email:', userEmail);
      fetchProjects();
    } else {
      console.warn('No githubUsername or userEmail available, skipping fetchProjects');
    }
  }, [githubUsername, userEmail, fetchProjects]);

  const fetchPullRequests = useCallback(async () => {
    if (!selectedProject) {
      console.log('No selected project for fetching pull requests');
      return;
    }
    if (!userEmail) {
      console.error('No user email available for fetching pull requests');
      setError('No user email available. Please log in again.');
      window.location.href = '/login';
      return;
    }
    setLoading(true);
    setError('');
    try {
      const url = `${API_BASE_URL}/admin/pull_requests/${encodeURIComponent(selectedProject)}`;
      console.log(`Fetching pull requests from: ${url}, with X-User-Email: ${userEmail}`);
      const response = await axios.get(url, {
        headers: { 'X-User-Email': userEmail }
      });
      console.log('Pull requests response:', response.data);
      setPullRequests(response.data.pullRequests || []);
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message;
      console.error('Error fetching pull requests:', err);
      console.error('Error details:', {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message
      });
      setError(`Failed to fetch pull requests: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  }, [selectedProject, userEmail]);

  useEffect(() => {
    fetchPullRequests();
  }, [fetchPullRequests]);

  const handleProjectChange = (e) => {
    const value = e.target.value;
    console.log('Project selected:', value);
    setSelectedProject(value);
  };

  const handleStatusChange = (e) => {
    const value = e.target.value;
    console.log('Status filter selected:', value);
    setStatusFilter(value);
  };

  const filteredPullRequests = statusFilter === 'all'
    ? pullRequests
    : pullRequests.filter(pr => pr.status.toLowerCase() === statusFilter.toLowerCase());

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Pull Request History</h1>

      {error && (
        <div style={styles.error}>
          {error}
        </div>
      )}

      <div style={styles.flexContainer}>
        <div style={styles.selectContainer}>
          <label style={styles.label}>Select Project</label>
          <select
            value={selectedProject}
            onChange={handleProjectChange}
            style={styles.select}
            disabled={loading || projects.length === 0}
          >
            {projects.length === 0 ? (
              <option value="">No projects available</option>
            ) : (
              projects.map(project => (
                <option key={project._id || project.name} value={project.name}>
                  {project.name}
                </option>
              ))
            )}
          </select>
        </div>

        <div style={styles.selectContainer}>
          <label style={styles.label}>Filter by Status</label>
          <select
            value={statusFilter}
            onChange={handleStatusChange}
            style={styles.select}
            disabled={loading}
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div style={styles.loading}>
          <svg style={styles.spinner} viewBox="0 0 24 24">
            <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8h8a8 8 0 01-16 0z" />
          </svg>
          Loading...
        </div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead style={styles.thead}>
              <tr>
                <th style={styles.th}>PR ID</th>
                <th style={styles.th}>Project</th>
                <th style={styles.th}>Developer</th>
                <th style={styles.th}>Timestamp</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Transaction Hash</th>
              </tr>
            </thead>
            <tbody style={styles.tbody}>
              {filteredPullRequests.length === 0 ? (
                <tr>
                  <td colSpan="6" style={styles.noData}>
                    No pull requests found.
                  </td>
                </tr>
              ) : (
                filteredPullRequests.map(pr => (
                  <tr key={pr.pullRequestId} style={styles.tr}>
                    <td style={styles.td}>{pr.pullRequestId}</td>
                    <td style={styles.td}>{pr.projectName}</td>
                    <td style={styles.td}>{pr.developer}</td>
                    <td style={styles.td}>{new Date(pr.timestamp).toLocaleString()}</td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.statusBadge,
                          ...(pr.status.toLowerCase() === 'pending'
                            ? styles.statusPending
                            : pr.status.toLowerCase() === 'approved'
                            ? styles.statusApproved
                            : styles.statusRejected),
                        }}
                      >
                        {pr.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {pr.txHash === 'N/A' ? (
                        'N/A'
                      ) : (
                        <a
                          href={`https://sepolia.etherscan.io/tx/${pr.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={styles.link}
                        >
                          {pr.txHash.slice(0, 6)}...{pr.txHash.slice(-4)}
                        </a>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AdminPullHistory;