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
  const [loading, setLoading] = useState(true);

  // On page load, check if user is already logged in (from localStorage)
  useEffect(() => {
    console.log('App useEffect running');
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        console.log('Parsed user from localStorage:', parsedUser);
        setUser(parsedUser);
      } catch (error) {
        console.error('Failed to parse user from localStorage:', error);
        localStorage.removeItem('user'); // Remove invalid data
      }
    }
    setLoading(false);
  }, []);

  // Clean up authToken and tempUserId when site is closed
  useEffect(() => {
    const handleBeforeUnload = () => {
      localStorage.removeItem('authToken');
      localStorage.removeItem('tempUserId');
      console.log('Cleaned up authToken and tempUserId on page unload');
    };

    // Listen for page unload (close/refresh)
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Cleanup event listeners
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Logout function to clear localStorage and user state
  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
    localStorage.removeItem('tempUserId');
    setUser(null);
    console.log('User logged out and localStorage cleared');
  };

  // Show loading while checking authentication
  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Router>
      <Routes>
        <Route 
          path="/" 
          element={
            user ? (
              (() => {
                console.log('Redirecting user:', user, 'to role:', user.role);
                const role = user.user?.role || user.role;
                
                // Map roles to routes safely
                const roleRoutes = {
                  'admin': '/admin',
                  'developer': '/dev',
                  'auditor': '/auditor'
                };
                
                const targetRoute = roleRoutes[role] || '/admin'; // Default fallback
                console.log('Target route:', targetRoute);
                
                return <Navigate to={targetRoute} replace />;
              })()
            ) : (
              <Login setUser={setUser} />
            )
          } 
        />
        <Route 
          path="/signup" 
          element={
            user ? (
              <Navigate to={`/${user.role}`} replace />
            ) : (
              <Signup />
            )
          } 
        />
        <Route 
          path="/admin" 
          element={
            user && (user.user?.role === 'admin' || user.role === 'admin') ? (
              <AdminDashboard onLogout={handleLogout} />
            ) : (
              <Navigate to="/" replace />
            )
          } 
        />
        {/* <Route 
          path="/dev" 
          element={
            user && user.role === 'developer' ? (
              <DevDashboard user={user} onLogout={handleLogout} />
            ) : (
              <Navigate to="/" replace />
            )
          } 
        />
        <Route 
          path="/auditor" 
          element={
            user && user.role === 'auditor' ? (
              <AuditorDashboard user={user} onLogout={handleLogout} />
            ) : (
              <Navigate to="/" replace />
            )
          } 
        /> */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;