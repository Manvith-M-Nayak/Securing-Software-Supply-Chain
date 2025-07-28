import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Signup() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: '',
    githubUsername: '',
    githubToken: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const {
      username,
      email,
      password,
      confirmPassword,
      role,
      githubUsername,
      githubToken
    } = formData;

    if (
      !username ||
      !email ||
      !password ||
      !confirmPassword ||
      !role ||
      !githubUsername ||
      !githubToken
    ) {
      setError('Please fill in all fields, including role, GitHub username, and GitHub token');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const requestBody = {
        username,
        email,
        password,
        role,
        githubUsername,
        githubToken
      };

      if (role === 'admin') {
        requestBody.createdProjects = [];
      } else if (role === 'developer') {
        requestBody.assignedProjects = [];
        requestBody.points = [];
      } else {
        requestBody.assignedProjects = [];
      }

      const response = await fetch('http://localhost:5001/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (response.ok) {
        const user = data.user;
        alert('Registration successful!');
        switch (user.role) {
          case 'admin':
            navigate('/admin');
            break;
          case 'developer':
            navigate('/dev');
            break;
          case 'auditor':
            navigate('/auditor');
            break;
          default:
            navigate('/dashboard');
        }
        setFormData({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          role: '',
          githubUsername: '',
          githubToken: ''
        });
      } else {
        throw new Error(data.error || data.message || 'Registration failed');
      }
    } catch (error) {
      console.error('Registration error:', error);
      setError('Registration failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRegister(e);
    }
  };

  const goToLogin = () => navigate('/login');

  return (
    <>
      <div className="container">
        <h1>Sign Up</h1>
        <div className="form-container">
          <div className="form-group">
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="Username"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Email"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <input
              type="text"
              name="githubUsername"
              value={formData.githubUsername}
              onChange={handleChange}
              placeholder="GitHub Username"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <input
              type="text"
              name="githubToken"
              value={formData.githubToken}
              onChange={handleChange}
              placeholder="GitHub Personal Access Token"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Password"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm Password"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              disabled={loading}
              onKeyPress={handleKeyPress}
            >
              <option value="">Select Role</option>
              <option value="developer">Developer</option>
              <option value="auditor">Auditor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleRegister}
            disabled={loading}
          >
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
          <div className="login-link">
            <p>Already have an account?</p>
            <button onClick={goToLogin}>Login</button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
      <style jsx>{`
        .container {
          font-family: 'Arial', sans-serif;
          background-color: #f4f6f9;
          margin: 50px auto;
          padding: 20px;
          max-width: 400px;
          color: #333;
        }
        h1 {
          font-size: 1.5rem;
          color: #1e3a8a;
          margin-bottom: 1.25rem;
          text-align: center;
        }
        .form-container {
          background-color: #fff;
          padding: 1.25rem;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .form-group {
          margin-bottom: 0.875rem;
          margin-right: 1.45rem;
        }
        input, select {
          width: 100%;
          padding: 0.625rem;
          border: 1px solid #d1d5db;
          border-radius: 5px;
          font-size: 0.875rem;
          background-color: #fff;
        }
        input:focus, select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        input:disabled, select:disabled {
          background-color: #e5e7eb;
          cursor: not-allowed;
        }
        button {
          width: 100%;
          padding: 0.625rem;
          background-color: #10b981;
          color: #fff;
          border: none;
          border-radius: 5px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        button:hover {
          background-color: #059669;
        }
        button:disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
        }
        .login-link {
          text-align: center;
          margin-top: 1.25rem;
        }
        .login-link p {
          margin: 0 0 0.5rem;
          color: #4b5563;
          font-size: 0.875rem;
        }
        .login-link button {
          background-color: #3b82f6;
        }
        .login-link button:hover {
          background-color: #1e3a8a;
        }
        .error {
          color: #ef4444;
          font-size: 0.875rem;
          margin-top: 0.875rem;
          text-align: center;
        }
        @media (max-width: 768px) {
          .container {
            padding: 10px;
            margin: 20px auto;
          }
          h1 {
            font-size: 1.25rem;
          }
          .form-container {
            padding: 1rem;
          }
          input, select, button {
            font-size: 0.75rem;
          }
        }
      `}</style>
    </>
  );
}

export default Signup;