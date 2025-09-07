"""
HTTPS listener implementation
"""

import ssl
import os
from typing import Dict, Any

from listeners.http import HTTPListener
from core.config import settings

class HTTPSListener(HTTPListener):
    """HTTPS listener with SSL/TLS support"""
    
    def __init__(self, listener_id: str, bind_address: str, bind_port: int, configuration: Dict[str, Any]):
        super().__init__(listener_id, bind_address, bind_port, configuration)
        
        # SSL configuration
        self.ssl_cert = configuration.get('ssl_cert')
        self.ssl_key = configuration.get('ssl_key')
        self.ssl_context = None
        
        # Setup SSL context
        self.setup_ssl()
    
    def setup_ssl(self):
        """Setup SSL context"""
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # Use provided cert/key or generate self-signed
        if self.ssl_cert and self.ssl_key:
            # Save cert and key to files
            cert_path = os.path.join(settings.SSL_CERT_DIR, f"{self.listener_id}.crt")
            key_path = os.path.join(settings.SSL_CERT_DIR, f"{self.listener_id}.key")
            
            with open(cert_path, 'w') as f:
                f.write(self.ssl_cert)
            
            with open(key_path, 'w') as f:
                f.write(self.ssl_key)
            
            self.ssl_context.load_cert_chain(cert_path, key_path)
        else:
            # Generate self-signed certificate
            self.generate_self_signed_cert()
    
    def generate_self_signed_cert(self):
        """Generate self-signed certificate"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Save to files
        cert_path = os.path.join(settings.SSL_CERT_DIR, f"{self.listener_id}.crt")
        key_path = os.path.join(settings.SSL_CERT_DIR, f"{self.listener_id}.key")
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        self.ssl_context.load_cert_chain(cert_path, key_path)
    
    async def start(self):
        """Start the HTTPS listener"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner,
            self.bind_address,
            self.bind_port,
            ssl_context=self.ssl_context
        )
        
        await self.site.start()
        
        print(f"HTTPS Listener started on {self.bind_address}:{self.bind_port}")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
