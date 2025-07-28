import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function Login({ setUser }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!username || !password) {
      setError('Please fill in both username and password');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await axios.post('http://localhost:5001/api/auth/login', {
        username,
        password
      });

      if (response.status === 200) {
        const responseData = response.data;
        console.log('Login response data:', responseData);
        
        // Extract the actual user data from the response
        const userData = responseData.user || responseData;
        console.log('Extracted user data:', userData);
        
        // Store the flat user data in localStorage
        localStorage.setItem('user', JSON.stringify(userData));
        
        // Update the user state in App component with flat data
        setUser(userData);
        
        // Navigation happens via App.js routing based on user role
      }
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = error.response?.data?.error || error.response?.data?.message || 'Login failed';
      setError('Login failed: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const goToSignup = () => {
    navigate('/signup');
  };

  return (
    <>
      <div className="container">
        <h1>Login</h1>
        <div className="form-container">
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                disabled={loading}
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
          <div className="signup-link">
            <p>Don't have an account?</p>
            <button onClick={goToSignup}>Sign Up</button>
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
          justify-content: center;  
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
        input {
          width: 100%;
          padding: 0.625rem;
          border: 1px solid #d1d5db;
          border-radius: 5px;
          font-size: 0.875rem;
        }
        input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        input:disabled {
          background-color: #e5e7eb;
          cursor: not-allowed;
        }
        button {
          width: 100%;
          padding: 0.625rem;
          background-color: #3b82f6;
          color: #fff;
          border: none;
          border-radius: 5px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        button:hover {
          background-color: #1e3a8a;
        }
        button:disabled {
          background-color: #9ca3af;
          cursor: not-allowed;
        }
        .signup-link {
          text-align: center;
          margin-top: 1.25rem;
        }
        .signup-link p {
          margin: 0 0 0.5rem;
          color: #4b5563;
          font-size: 0.875rem;
        }
        .signup-link button {
          background-color: #10b981;
        }
        .signup-link button:hover {
          background-color: #059669;
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
          input, button {
            font-size: 0.75rem;
          }
        }
      `}</style>
    </>
  );
}

export default Login;