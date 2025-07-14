import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Signup() {
  /* ------------------------------------------------------------------
     React Router hook for programmatic navigation
  ------------------------------------------------------------------ */
  const navigate = useNavigate();

  /* ------------------------------------------------------------------
     Form state now has seven properties, including githubToken
  ------------------------------------------------------------------ */
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: '',
    githubUsername: '',
    githubToken: ''          // NEW FIELD
  });

  /* ------------------------------------------------------------------
     Loading flag disables inputs and shows a spinner label
  ------------------------------------------------------------------ */
  const [loading, setLoading] = useState(false);

  /* ------------------------------------------------------------------
     Generic change handler – updates only the key that triggered it
  ------------------------------------------------------------------ */
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  /* ------------------------------------------------------------------
     Main register handler – validates, builds request, and posts
  ------------------------------------------------------------------ */
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

    /* --------------------------------------------------------------
       1) Field completeness check – note githubToken is required
    -------------------------------------------------------------- */
    if (
      !username ||
      !email ||
      !password ||
      !confirmPassword ||
      !role ||
      !githubUsername ||
      !githubToken
    ) {
      alert('Please fill in all fields, including role, GitHub username, and GitHub token');
      return;
    }

    /* --------------------------------------------------------------
       2) Password confirmation
    -------------------------------------------------------------- */
    if (password !== confirmPassword) {
      alert('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      /* ------------------------------------------------------------
         3) Assemble request payload
      ------------------------------------------------------------ */
      const requestBody = {
        username,
        email,
        password,
        role,
        githubUsername,
        githubToken
      };

      /* ------------------------------------------------------------
         4) Role‑specific initial project arrays
      ------------------------------------------------------------ */
      if (role === 'admin') {
        requestBody.createdProjects = [];
      } else {
        requestBody.assignedProjects = [];
      }

      /* ------------------------------------------------------------
         5) POST to backend
      ------------------------------------------------------------ */
      const response = await fetch('http://localhost:5001/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      /* ------------------------------------------------------------
         6) Handle success
      ------------------------------------------------------------ */
      if (response.ok) {
        const user = data.user;
        alert('Registration successful! You are now logged in.');

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

        /* --------------------------------------------------------
           7) Reset form
        -------------------------------------------------------- */
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
      alert('Registration failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  /* ------------------------------------------------------------------
     Allow Enter key to submit when focus is on <select>
  ------------------------------------------------------------------ */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRegister(e);
    }
  };

  /* ------------------------------------------------------------------
     Navigate to login page
  ------------------------------------------------------------------ */
  const goToLogin = () => navigate('/login');

  /* ------------------------------------------------------------------
     JSX – unchanged layout except for new GitHub token field
  ------------------------------------------------------------------ */
  return (
    <div style={{ maxWidth: '400px', margin: '50px auto', padding: '20px' }}>
      <h2>Sign Up</h2>
      <div>
        {/* Username */}
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

        {/* Email */}
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

        {/* GitHub Username */}
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

        {/* GitHub Token – NEW FIELD */}
        <div style={{ marginBottom: '15px' }}>
          <input
            type="text"
            name="githubToken"
            value={formData.githubToken}
            onChange={handleChange}
            placeholder="GitHub Personal Access Token"
            style={inputStyle}
            disabled={loading}
          />
        </div>

        {/* Password */}
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

        {/* Confirm Password */}
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

        {/* Role selector */}
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

        {/* Submit button */}
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

      {/* Link to login */}
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

/* ------------------------------------------------------------------
   Reusable inline‐style object for inputs
------------------------------------------------------------------ */
const inputStyle = {
  width: '100%',
  padding: '10px',
  border: '1px solid #ccc',
  borderRadius: '4px'
};

export default Signup;
