// client/src/hooks/useWebSocket.js
import { useContext, useEffect, useCallback } from 'react';
import { WebSocketContext } from '../contexts/WebSocketContext';

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  
  return context;
}

// Hook for subscribing to WebSocket channels
export function useWebSocketSubscription(channel, callback) {
  const { subscribe } = useWebSocket();
  
  useEffect(() => {
    if (!channel || !callback) return;
    
    const unsubscribe = subscribe(channel, callback);
    return unsubscribe;
  }, [channel, callback, subscribe]);
}

// Hook for agent-specific subscriptions
export function useAgentSubscription(agentId, onUpdate) {
  const memoizedCallback = useCallback(onUpdate, [agentId]);
  
  useWebSocketSubscription(
    agentId ? `agent:${agentId}` : null,
    memoizedCallback
  );
}

// Hook for command output subscriptions
export function useCommandOutput(agentId, onOutput) {
  const memoizedCallback = useCallback(onOutput, [agentId]);
  
  useWebSocketSubscription(
    agentId ? `agent:${agentId}:output` : null,
    memoizedCallback
  );
}

// Hook for notifications
export function useNotifications(onNotification) {
  useWebSocketSubscription('notifications', onNotification);
}

// Hook for alerts
export function useAlerts(onAlert) {
  useWebSocketSubscription('alerts', onAlert);
}
