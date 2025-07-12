import React, { useState } from 'react';

function Signup() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: '',
    githubUsername: '',
    assignedProjects: [] // New field for assigned projects
  });

  const [loading, setLoading] = useState(false);
  const [projectInput, setProjectInput] = useState(''); // For adding projects

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const addProject = () => {
    if (projectInput.trim() && !formData.assignedProjects.includes(projectInput.trim())) {
      setFormData(prevState => ({
        ...prevState,
        assignedProjects: [...prevState.assignedProjects, projectInput.trim()]
      }));
      setProjectInput('');
    }
  };

  const removeProject = (projectToRemove) => {
    setFormData(prevState => ({
      ...prevState,
      assignedProjects: prevState.assignedProjects.filter(project => project !== projectToRemove)
    }));
  };

  const handleRegister = async (e) => {
    e.preventDefault();

    const { username, email, password, confirmPassword, role, githubUsername, assignedProjects } = formData;

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
      // Using fetch instead of axios since axios import was removed
      const response = await fetch('http://localhost:5001/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
          role,
          githubUsername,
          assignedProjects
        })
      });

      const data = await response.json();

      if (response.ok) {
        const user = data.user;

        alert('Registration successful! You are now logged in.');
        
        // Note: In a real app, you'd navigate based on user role
        // For this demo, we'll just show success
        console.log('User registered:', user);
        
        // Reset form after successful registration
        setFormData({
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          role: '',
          githubUsername: '',
          assignedProjects: []
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
    alert('In a real app, this would navigate to login page');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addProject();
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
          >
            <option value="">Select Role</option>
            <option value="developer">Developer</option>
            <option value="auditor">Auditor</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {/* Assigned Projects Section */}
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Assigned Projects (Optional)
          </label>
          <div style={{ display: 'flex', gap: '5px', marginBottom: '10px' }}>
            <input
              type="text"
              value={projectInput}
              onChange={(e) => setProjectInput(e.target.value)}
              placeholder="Enter project name"
              style={{ ...inputStyle, flex: 1 }}
              disabled={loading}
              onKeyPress={handleKeyPress}
            />
            <button
              type="button"
              onClick={addProject}
              disabled={loading || !projectInput.trim()}
              style={{
                padding: '10px 15px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading || !projectInput.trim() ? 'not-allowed' : 'pointer'
              }}
            >
              Add
            </button>
          </div>
          
          {/* Display assigned projects */}
          {formData.assignedProjects.length > 0 && (
            <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '10px' }}>
              <strong>Assigned Projects:</strong>
              <div style={{ marginTop: '5px' }}>
                {formData.assignedProjects.map((project, index) => (
                  <div key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '5px',
                    backgroundColor: '#f8f9fa',
                    marginBottom: '5px',
                    borderRadius: '3px'
                  }}>
                    <span>{project}</span>
                    <button
                      type="button"
                      onClick={() => removeProject(project)}
                      disabled={loading}
                      style={{
                        padding: '2px 6px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontSize: '12px'
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
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