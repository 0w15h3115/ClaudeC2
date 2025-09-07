"""
Listener manager for handling multiple listeners
"""

import asyncio
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from core.database import SessionLocal
from core.models import Listener
from listeners.http import HTTPListener
from listeners.https import HTTPSListener
from listeners.dns import DNSListener
from listeners.websocket import WebSocketListener

class ListenerManager:
    """Manages all active listeners"""
    
    def __init__(self):
        self.listeners: Dict[str, Any] = {}
        self.threads: Dict[str, threading.Thread] = {}
        
    def get_listener_class(self, listener_type: str):
        """Get listener class by type"""
        listener_map = {
            "http": HTTPListener,
            "https": HTTPSListener,
            "dns": DNSListener,
            "websocket": WebSocketListener
        }
        return listener_map.get(listener_type)
    
    async def start_listener(self, listener_id: str, config: Any):
        """Start a listener"""
        # Get listener class
        listener_class = self.get_listener_class(config.type)
        if not listener_class:
            raise ValueError(f"Unknown listener type: {config.type}")
        
        # Create listener instance
        listener = listener_class(
            listener_id=listener_id,
            bind_address=config.bind_address,
            bind_port=config.bind_port,
            configuration=config.configuration
        )
        
        # Store listener
        self.listeners[listener_id] = listener
        
        # Start listener in thread
        thread = threading.Thread(
            target=self._run_listener,
            args=(listener,),
            daemon=True
        )
        thread.start()
        self.threads[listener_id] = thread
        
        # Update database
        db = SessionLocal()
        try:
            db_listener = db.query(Listener).filter(
                Listener.id == listener_id
            ).first()
            if db_listener:
                db_listener.is_running = True
                db.commit()
        finally:
            db.close()
    
    def _run_listener(self, listener):
        """Run listener in thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(listener.start())
        except Exception as e:
            print(f"Listener error: {e}")
        finally:
            loop.close()
    
    def stop_listener(self, listener_id: str):
        """Stop a listener"""
        if listener_id in self.listeners:
            # Stop the listener
            listener = self.listeners[listener_id]
            asyncio.create_task(listener.stop())
            
            # Remove from tracking
            del self.listeners[listener_id]
            
            # Thread will exit naturally
            if listener_id in self.threads:
                del self.threads[listener_id]
            
            # Update database
            db = SessionLocal()
            try:
                db_listener = db.query(Listener).filter(
                    Listener.id == listener_id
                ).first()
                if db_listener:
                    db_listener.is_running = False
                    db.commit()
            finally:
                db.close()
    
    def is_running(self, listener_id: str) -> bool:
        """Check if listener is running"""
        return listener_id in self.listeners
    
    def get_listener(self, listener_id: str) -> Optional[Any]:
        """Get listener instance"""
        return self.listeners.get(listener_id)
    
    def get_all_listeners(self) -> Dict[str, Any]:
        """Get all active listeners"""
        return self.listeners.copy()
    
    def stop_all(self):
        """Stop all listeners"""
        for listener_id in list(self.listeners.keys()):
            self.stop_listener(listener_id)

# Global listener manager instance
listener_manager = ListenerManager()
