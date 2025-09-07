// client/src/services/auth.js
import apiService, { api } from './api';

class AuthService {
  constructor() {
    this.user = null;
    this.token = localStorage.getItem('authToken');
    this.refreshToken = localStorage.getItem('refreshToken');
    this.tokenRefreshTimer = null;
  }
  
  async login(username, password) {
    try {
      console.log('Attempting login with:', username);
      const response = await api.login({ username, password });
      console.log('Login response:', response);
      
      if (response.access_token) {
        console.log('Setting tokens and user data');
        this.setTokens(response.access_token, response.refresh_token);
        this.user = response.user;
        console.log('User set to:', this.user);
        this.startTokenRefresh();
        
        return { success: true, user: this.user };
      }
      
      throw new Error('Invalid response from server');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }
  
  async logout() {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearTokens();
      this.user = null;
      this.stopTokenRefresh();
    }
  }
  
  async getCurrentUser() {
    if (!this.token) {
      return null;
    }
    
    try {
      this.user = await api.me();
      return this.user;
    } catch (error) {
      console.error('Failed to get current user:', error);
      if (error.message === 'Unauthorized') {
        await this.refreshAccessToken();
      }
      return null;
    }
  }
  
  async refreshAccessToken() {
    if (!this.refreshToken) {
      this.clearTokens();
      return false;
    }
    
    try {
      const response = await api.refresh();
      if (response.access_token) {
        this.setTokens(response.access_token, response.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.clearTokens();
    }
    
    return false;
  }
  
  setTokens(accessToken, refreshToken) {
    this.token = accessToken;
    this.refreshToken = refreshToken;
    
    localStorage.setItem('authToken', accessToken);
    if (refreshToken) {
      localStorage.setItem('refreshToken', refreshToken);
    }
    
    apiService.setToken(accessToken);
  }
  
  clearTokens() {
    this.token = null;
    this.refreshToken = null;
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    
    apiService.setToken(null);
  }
  
  startTokenRefresh() {
    // Refresh token every 25 minutes (assuming 30 min expiry)
    this.tokenRefreshTimer = setInterval(async () => {
      await this.refreshAccessToken();
    }, 25 * 60 * 1000);
  }
  
  stopTokenRefresh() {
    if (this.tokenRefreshTimer) {
      clearInterval(this.tokenRefreshTimer);
      this.tokenRefreshTimer = null;
    }
  }
  
  isAuthenticated() {
    return !!this.token;
  }
  
  getToken() {
    return this.token;
  }
  
  getUser() {
    return this.user;
  }
  
  // Role-based access control
  hasRole(role) {
    return this.user?.roles?.includes(role) || false;
  }
  
  hasPermission(permission) {
    return this.user?.permissions?.includes(permission) || false;
  }
  
  canAccess(resource) {
    const permissions = {
      agents: ['agents.view', 'admin'],
      tasks: ['tasks.view', 'admin'],
      settings: ['settings.view', 'admin'],
      payloads: ['payloads.generate', 'admin'],
    };
    
    const requiredPermissions = permissions[resource] || [];
    return requiredPermissions.some(perm => this.hasPermission(perm));
  }
}

// Create singleton instance
const authService = new AuthService();

export default authService;
