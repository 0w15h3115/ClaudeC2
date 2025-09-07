// client/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
    this.token = localStorage.getItem('authToken');
  }
  
  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('authToken', token);
    } else {
      localStorage.removeItem('authToken');
    }
  }
  
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    return headers;
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    };
    
    try {
      const response = await fetch(url, config);
      
      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.setToken(null);
        window.location.href = '/login';
        throw new Error('Unauthorized');
      }
      
      // Handle other errors
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || `HTTP error! status: ${response.status}`);
      }
      
      // Handle empty responses
      const text = await response.text();
      return text ? JSON.parse(text) : null;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }
  
  // HTTP Methods
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }
  
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  async patch(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }
  
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
  
  // File upload
  async upload(endpoint, formData) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  // Download file
  async download(endpoint) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }
}

// Create singleton instance
const apiService = new ApiService();

// API endpoints
export const api = {
  // Auth
  login: (credentials) => apiService.post('/api/auth/login', credentials),
  logout: () => apiService.post('/api/auth/logout'),
  refresh: () => apiService.post('/api/auth/refresh'),
  me: () => apiService.get('/api/auth/me'),
  
  // Agents
  agents: {
    list: (params) => apiService.get('/api/agents', params),
    get: (id) => apiService.get(`/api/agents/${id}`),
    delete: (id) => apiService.delete(`/api/agents/${id}`),
    reconnect: (id) => apiService.post(`/api/agents/${id}/reconnect`),
    upload: (id, formData) => apiService.upload(`/api/agents/${id}/upload`, formData),
    download: (id, path) => apiService.post(`/api/agents/${id}/download`, { path }),
  },
  
  // Tasks
  tasks: {
    list: (params) => apiService.get('/api/tasks', params),
    get: (id) => apiService.get(`/api/tasks/${id}`),
    create: (agentId, task) => apiService.post(`/api/agents/${agentId}/tasks`, task),
    cancel: (id) => apiService.post(`/api/tasks/${id}/cancel`),
    output: (id) => apiService.get(`/api/tasks/${id}/output`),
  },
  
  // Listeners
  listeners: {
    list: () => apiService.get('/api/listeners'),
    get: (id) => apiService.get(`/api/listeners/${id}`),
    create: (listener) => apiService.post('/api/listeners', listener),
    update: (id, data) => apiService.patch(`/api/listeners/${id}`, data),
    delete: (id) => apiService.delete(`/api/listeners/${id}`),
    start: (id) => apiService.post(`/api/listeners/${id}/start`),
    stop: (id) => apiService.post(`/api/listeners/${id}/stop`),
  },
  
  // Payloads
  payloads: {
    list: () => apiService.get('/api/payloads'),
    generate: (config) => apiService.post('/api/payloads/generate', config),
    download: (id) => apiService.download(`/api/payloads/${id}/download`),
  },
  
  // Stats
  stats: {
    dashboard: () => apiService.get('/api/stats'),
    timeline: (range) => apiService.get('/api/stats/timeline', { range }),
    activity: () => apiService.get('/api/activity/recent'),
  },
  
  // Settings
  settings: {
    get: () => apiService.get('/api/settings'),
    update: (settings) => apiService.put('/api/settings', settings),
  },
};

export default apiService;
