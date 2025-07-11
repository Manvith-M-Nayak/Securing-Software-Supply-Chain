import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Pages
import Login from './pages/Login';
import Signup from './pages/Signup';
import AdminDashboard from './pages/AdminDashboard';
// import DevDashboard from './pages/DevDashboard';
// import AuditorDashboard from './pages/AuditorDashboard';

function App() {
  const [user, setUser] = useState(null);

  // On page load, check if user is already logged in (from localStorage)
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      } catch (error) {
        console.error('Failed to parse user from localStorage:', error);
      }
    }
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/"        element={user ? <Navigate to={`/${user.role}`} /> : <Login setUser={setUser} />} />
        <Route path="/signup"  element={user ? <Navigate to={`/${user.role}`} /> : <Signup />} />
        <Route path="/admin"   element={user && user.role === 'admin'    ? <AdminDashboard   user={user} /> : <Navigate to="/" />} />
        {/* <Route path="/dev"     element={user && user.role === 'developer'? <DevDashboard     user={user} /> : <Navigate to="/" />} />
        <Route path="/auditor" element={user && user.role === 'auditor'  ? <AuditorDashboard user={user} /> : <Navigate to="/" />} /> */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default App;
