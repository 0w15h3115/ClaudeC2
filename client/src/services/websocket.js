// client/src/services/websocket.js
import authService from './auth';

const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.subscribers = new Map();
    this.connectionStatus = 'disconnected';
    this.statusListeners = new Set();
  }
  
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }
    
    const token = authService.getToken();
    if (!token) {
      console.error('No auth token available for WebSocket connection');
      return;
    }
    
    this.setConnectionStatus('connecting');
    
    try {
      this.ws = new WebSocket(`${WS_BASE_URL}?token=${token}`);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.setConnectionStatus('connected');
        this.reconnectAttempts = 0;
        
        // Resubscribe to all channels
        this.subscribers.forEach((callbacks, channel) => {
          this.sendMessage({
            type: 'subscribe',
            channel: channel
          });
        });
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.setConnectionStatus('error');
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.setConnectionStatus('disconnected');
        this.ws = null;
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.setConnectionStatus('error');
      this.scheduleReconnect();
    }
  }
  
  disconnect() {
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setConnectionStatus('disconnected');
  }
  
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.setConnectionStatus('error');
      return;
    }
    
    this.clearReconnectTimer();
    
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds
    );
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }
  
  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
  
  setConnectionStatus(status) {
    this.connectionStatus = status;
    this.statusListeners.forEach(listener => listener(status));
  }
  
  onStatusChange(callback) {
    this.statusListeners.add(callback);
    // Return unsubscribe function
    return () => this.statusListeners.delete(callback);
  }
  
  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }
  
  handleMessage(data) {
    const { type, channel, payload } = data;
    
    switch (type) {
      case 'message':
        this.notifySubscribers(channel, payload);
        break;
        
      case 'notification':
        this.notifySubscribers('notifications', payload);
        break;
        
      case 'ping':
        this.sendMessage({ type: 'pong' });
        break;
        
      case 'error':
        console.error('WebSocket error message:', payload);
        break;
        
      default:
        console.warn('Unknown message type:', type);
    }
  }
  
  subscribe(channel, callback) {
    if (!this.subscribers.has(channel)) {
      this.subscribers.set(channel, new Set());
      
      // Send subscribe message if connected
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({
          type: 'subscribe',
          channel: channel
        });
      }
    }
    
    this.subscribers.get(channel).add(callback);
    
    // Return unsubscribe function
    return () => this.unsubscribe(channel, callback);
  }
  
  unsubscribe(channel, callback) {
    const callbacks = this.subscribers.get(channel);
    if (callbacks) {
      callbacks.delete(callback);
      
      // If no more callbacks, remove channel and unsubscribe
      if (callbacks.size === 0) {
        this.subscribers.delete(channel);
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.sendMessage({
            type: 'unsubscribe',
            channel: channel
          });
        }
      }
    }
  }
  
  notifySubscribers(channel, data) {
    const callbacks = this.subscribers.get(channel);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in WebSocket subscriber callback:', error);
        }
      });
    }
  }
  
  // Convenience methods for common channels
  subscribeToAgent(agentId, callback) {
    return this.subscribe(`agent:${agentId}`, callback);
  }
  
  subscribeToAgentOutput(agentId, callback) {
    return this.subscribe(`agent:${agentId}:output`, callback);
  }
  
  subscribeToAgentScreenshot(agentId, callback) {
    return this.subscribe(`agent:${agentId}:screenshot`, callback);
  }
  
  subscribeToNotifications(callback) {
    return this.subscribe('notifications', callback);
  }
  
  subscribeToAlerts(callback) {
    return this.subscribe('alerts', callback);
  }
  
  // Send typed messages
  sendCommand(agentId, command) {
    this.sendMessage({
      type: 'command',
      agentId: agentId,
      payload: command
    });
  }
  
  getConnectionStatus() {
    return this.connectionStatus;
  }
  
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
const wsService = new WebSocketService();

export default wsService;
