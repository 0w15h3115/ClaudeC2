"""
HTTPS transport for agent communications
"""

import ssl
import requests
from .http import HTTPTransport

class HTTPSTransport(HTTPTransport):
    """HTTPS transport implementation with SSL/TLS support"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Configure SSL/TLS settings
        if config.verify_ssl:
            self.session.verify = True
        else:
            self.session.verify = False
            # Disable SSL warnings for self-signed certificates
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Set up client certificate authentication if provided
        if hasattr(config, 'client_cert_path') and config.client_cert_path:
            self.session.cert = config.client_cert_path
            
        # Configure SSL context for additional security
        self.ssl_context = ssl.create_default_context()
        if not config.verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE