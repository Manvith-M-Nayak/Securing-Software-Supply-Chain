// src/pages/Login.jsx
import React, { useState } from 'react';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const loginUser = () => {
    if (username && password) {
      onLogin({ username });
    } else {
      alert('Please enter both fields');
    }
  };

  return (
    <div>
      <h2>Login</h2>
      <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
      <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Password" />
      <button onClick={loginUser}>Login</button>
    </div>
  );
}

export default Login;
