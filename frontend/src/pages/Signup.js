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
    githubUsername: ''
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleRegister = async (e) => {
    e.preventDefault();

    const { username, email, password, confirmPassword, role, githubUsername } = formData;

    if (!username || !email || !password || !confirmPassword || !role || !githubUsername) {
      alert('Please fill in all fields, including role and GitHub username');
      return;
    }

    if (password !== confirmPassword) {
      alert('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      // Prepare request body with empty project arrays based on role
      const requestBody = {
        username,
        email,
        password,
        role,
        githubUsername
      };

      // Add the appropriate empty projects field based on role
      if (role === 'admin') {
        requestBody.createdProjects = [];
      } else {
        requestBody.assignedProjects = [];
      }

      const response = await fetch('http://localhost:5001/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (response.ok) {
        const user = data.user;

        alert('Registration successful! You are now logged in.');
        
        // Navigate to the appropriate page based on user role
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
            navigate('/dashboard'); // fallback route
        }
        
        // Reset form after successful registration
        setFormData({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          role: '',
          githubUsername: ''
        });
      } else {
        throw new Error(data.error || data.message || 'Registration failed');
      }

    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const goToLogin = () => {
    navigate('/login');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRegister(e);
    }
  };

  return (
    <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px' }}>
      <h2>Sign Up</h2>
      <div>
        <div style={{ marginBottom: '15px' }}>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            placeholder="Username"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            placeholder="Email"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <input
            type="text"
            name="githubUsername"
            value={formData.githubUsername}
            onChange={handleChange}
            placeholder="GitHub Username"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Password"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <input
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Confirm Password"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <select
            name="role"
            value={formData.role}
            onChange={handleChange}
            style={inputStyle}
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
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: loading ? '#ccc' : '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            marginBottom: '10px'
          }}
        >
          {loading ? 'Creating Account...' : 'Sign Up'}
        </button>
      </div>

      <div style={{ textAlign: 'center', marginTop: '20px' }}>
        <p>Already have an account?</p>
        <button
          onClick={goToLogin}
          style={{
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Login
        </button>
      </div>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '10px',
  border: '1px solid #ccc',
  borderRadius: '4px'
};

export default Signup;