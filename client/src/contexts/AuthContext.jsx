// client/src/contexts/AuthContext.jsx
import React, { createContext, useState, useEffect, useCallback } from 'react';
import authService from '../services/auth';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    checkAuth();
  }, []);
  
  const checkAuth = async () => {
    try {
      if (authService.isAuthenticated()) {
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const result = await authService.login(username, password);
      setUser(result.user);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);
  
  const logout = useCallback(async () => {
    try {
      await authService.logout();
      setUser(null);
    } catch (err) {
      console.error('Logout error:', err);
    }
  }, []);
  
  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);
  
  const hasRole = useCallback((role) => {
    return authService.hasRole(role);
  }, []);
  
  const hasPermission = useCallback((permission) => {
    return authService.hasPermission(permission);
  }, []);
  
  const canAccess = useCallback((resource) => {
    return authService.canAccess(resource);
  }, []);
  
  const value = {
    user,
    loading,
    error,
    login,
    logout,
    refreshUser,
    hasRole,
    hasPermission,
    canAccess,
    isAuthenticated: !!user,
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
