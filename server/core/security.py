"""
Security utilities for authentication and encryption
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    """Decode JWT access token and return username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except jwt.PyJWTError:
        return None

def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode()

def encrypt_data(data: str, key: str) -> str:
    """Encrypt data using Fernet"""
    f = Fernet(key.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str, key: str) -> str:
    """Decrypt data using Fernet"""
    f = Fernet(key.encode())
    return f.decrypt(encrypted_data.encode()).decode()

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def create_default_admin():
    """Create default admin user if it doesn't exist"""
    print(f"Creating default admin user with username: {settings.DEFAULT_ADMIN_USERNAME}")
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
        if not admin:
            print(f"Admin user not found, creating new user...")
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email="admin@c2.local",
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin"
            )
            db.add(admin)
            db.commit()
            print(f"Default admin user created: {settings.DEFAULT_ADMIN_USERNAME}")
        else:
            print(f"Admin user already exists: {admin.username}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

def validate_agent_token(token: str) -> bool:
    """Validate agent authentication token"""
    # Implement agent-specific token validation
    # This could be a separate JWT with different claims
    # or a different authentication mechanism
    try:
        # For now, we'll use a simple check
        # In production, implement proper agent authentication
        return len(token) == 64 and token.isalnum()
    except:
        return False

def hash_file(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    import hashlib
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

class RateLimiter:
    """Simple rate limiter for API endpoints"""
    def __init__(self):
        self.attempts = {}
    
    def is_allowed(self, key: str, max_attempts: int = 5, window: int = 300) -> bool:
        """Check if request is allowed based on rate limit"""
        now = datetime.utcnow()
        
        # Clean old entries
        self.attempts = {
            k: v for k, v in self.attempts.items()
            if (now - v['first']).total_seconds() < window
        }
        
        if key not in self.attempts:
            self.attempts[key] = {'count': 1, 'first': now}
            return True
        
        if self.attempts[key]['count'] >= max_attempts:
            return False
        
        self.attempts[key]['count'] += 1
        return True

# Global rate limiter instance
rate_limiter = RateLimiter()
