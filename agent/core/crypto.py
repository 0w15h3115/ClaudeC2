# agent/core/crypto.py
import os
import json
import base64
import hashlib
from typing import Dict, Any, Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    """Handles all cryptographic operations for the agent"""
    
    def __init__(self, key: str):
        self.key = key
        self.fernet = self._create_fernet(key)
        self.session_key = None
        self.rsa_private_key = None
        self.rsa_public_key = None
        self.server_public_key = None
        
    def _create_fernet(self, key: str) -> Fernet:
        """Create Fernet instance from key"""
        # Derive a proper key from the provided string
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'c2_agent_salt',  # In production, use random salt
            iterations=100000,
            backend=default_backend()
        )
        key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(key_bytes)
    
    def generate_rsa_keypair(self, key_size: int = 2048):
        """Generate RSA key pair"""
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        self.rsa_public_key = self.rsa_private_key.public_key()
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        if not self.rsa_public_key:
            self.generate_rsa_keypair()
        
        pem = self.rsa_public_key.public_key_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
    
    def set_server_public_key(self, pem_data: str):
        """Set server's public key from PEM data"""
        self.server_public_key = serialization.load_pem_public_key(
            pem_data.encode('utf-8'),
            backend=default_backend()
        )
    
    def encrypt_data(self, data: Union[str, bytes, dict]) -> str:
        """Encrypt data using Fernet"""
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self.fernet.encrypt(data)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, dict]:
        """Decrypt data using Fernet"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = self.fernet.decrypt(encrypted_bytes)
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted.decode('utf-8'))
            except json.JSONDecodeError:
                return decrypted.decode('utf-8')
                
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_with_rsa(self, data: bytes, public_key=None) -> bytes:
        """Encrypt data with RSA public key"""
        key = public_key or self.server_public_key
        if not key:
            raise Exception("No RSA public key available")
        
        encrypted = key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted
    
    def decrypt_with_rsa(self, encrypted_data: bytes) -> bytes:
        """Decrypt data with RSA private key"""
        if not self.rsa_private_key:
            raise Exception("No RSA private key available")
        
        decrypted = self.rsa_private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted
    
    def generate_session_key(self) -> str:
        """Generate a new session key"""
        self.session_key = Fernet.generate_key()
        return base64.b64encode(self.session_key).decode('utf-8')
    
    def encrypt_session(self, data: Union[str, bytes, dict]) -> str:
        """Encrypt data with session key"""
        if not self.session_key:
            raise Exception("No session key available")
        
        fernet = Fernet(self.session_key)
        
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = fernet.encrypt(data)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt_session(self, encrypted_data: str) -> Union[str, dict]:
        """Decrypt data with session key"""
        if not self.session_key:
            raise Exception("No session key available")
        
        fernet = Fernet(self.session_key)
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = fernet.decrypt(encrypted_bytes)
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted.decode('utf-8'))
            except json.JSONDecodeError:
                return decrypted.decode('utf-8')
                
        except Exception as e:
            raise Exception(f"Session decryption failed: {e}")
    
    def compute_hash(self, data: Union[str, bytes]) -> str:
        """Compute SHA256 hash of data"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        digest = hashlib.sha256(data).hexdigest()
        return digest
    
    def verify_hash(self, data: Union[str, bytes], expected_hash: str) -> bool:
        """Verify data against expected hash"""
        computed_hash = self.compute_hash(data)
        return computed_hash == expected_hash
    
    def obfuscate_string(self, data: str) -> str:
        """Simple string obfuscation (not cryptographically secure)"""
        # XOR with key
        key_bytes = self.key.encode('utf-8')
        data_bytes = data.encode('utf-8')
        
        result = bytearray()
        for i, byte in enumerate(data_bytes):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return base64.b64encode(result).decode('utf-8')
    
    def deobfuscate_string(self, obfuscated: str) -> str:
        """Deobfuscate string"""
        try:
            data_bytes = base64.b64decode(obfuscated)
            key_bytes = self.key.encode('utf-8')
            
            result = bytearray()
            for i, byte in enumerate(data_bytes):
                result.append(byte ^ key_bytes[i % len(key_bytes)])
            
            return result.decode('utf-8')
        except Exception:
            return obfuscated
