"""
Shared encryption utilities
"""

import os
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

class AESCrypto:
    """AES encryption/decryption"""
    
    def __init__(self, key: str):
        self.key = base64.b64decode(key)
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data with AES-256-CBC"""
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        return base64.b64encode(iv + ciphertext)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data with AES-256-CBC"""
        data = base64.b64decode(ciphertext)
        iv = data[:AES.block_size]
        ciphertext = data[AES.block_size:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return plaintext
    
    @staticmethod
    def generate_key() -> str:
        """Generate new AES-256 key"""
        return base64.b64encode(get_random_bytes(32)).decode()
