// src/App.jsx
import React, { useState } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

function App() {
  const [user, setUser] = useState(null);

  return (
    <div>
      {user ? (
        <Dashboard user={user} />
      ) : (
        <Login onLogin={setUser} />
      )}
    </div>
  );
}

export default App;
