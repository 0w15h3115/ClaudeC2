// client/src/contexts/WebSocketContext.jsx
import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import wsService from '../services/websocket';

export const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [notifications, setNotifications] = useState([]);
  const statusUnsubscribeRef = useRef(null);
  const notificationUnsubscribeRef = useRef(null);
  
  useEffect(() => {
    if (isAuthenticated) {
      // Connect WebSocket
      wsService.connect();
      
      // Subscribe to connection status changes
      statusUnsubscribeRef.current = wsService.onStatusChange(setConnectionStatus);
      
      // Subscribe to notifications
      notificationUnsubscribeRef.current = wsService.subscribeToNotifications((notification) => {
        setNotifications(prev => [...prev, {
          ...notification,
          id: Date.now(),
          timestamp: new Date().toISOString()
        }]);
      });
    } else {
      // Disconnect WebSocket
      wsService.disconnect();
    }
    
    return () => {
      // Cleanup subscriptions
      if (statusUnsubscribeRef.current) {
        statusUnsubscribeRef.current();
      }
      if (notificationUnsubscribeRef.current) {
        notificationUnsubscribeRef.current();
      }
    };
  }, [isAuthenticated]);
  
  const subscribe = useCallback((channel, callback) => {
    return wsService.subscribe(channel, callback);
  }, []);
  
  const unsubscribe = useCallback((channel, callback) => {
    wsService.unsubscribe(channel, callback);
  }, []);
  
  const sendMessage = useCallback((message) => {
    wsService.sendMessage(message);
  }, []);
  
  const sendCommand = useCallback((agentId, command) => {
    wsService.sendCommand(agentId, command);
  }, []);
  
  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);
  
  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(notif => notif.id !== id));
  }, []);
  
  const value = {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    notifications,
    subscribe,
    unsubscribe,
    sendMessage,
    sendCommand,
    clearNotifications,
    removeNotification,
  };
  
  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}
