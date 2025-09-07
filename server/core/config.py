"""
Server configuration management
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "C2 Team Server"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./c2_teamserver.db"
    # For PostgreSQL: "postgresql://user:password@localhost/c2db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme123!")
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # File storage
    UPLOAD_DIR: str = "./uploads"
    DOWNLOAD_DIR: str = "./downloads"
    PAYLOAD_DIR: str = "./payloads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Listener defaults
    LISTENER_CHECK_INTERVAL: int = 30  # seconds
    LISTENER_TIMEOUT: int = 300  # seconds
    
    # HTTP Listener
    HTTP_LISTENER_ENABLED: bool = False
    HTTP_LISTENER_HOST: str = "0.0.0.0"
    HTTP_LISTENER_PORT: int = 8080
    
    # DNS Listener  
    DNS_LISTENER_ENABLED: bool = False
    DNS_LISTENER_HOST: str = "0.0.0.0"
    DNS_LISTENER_PORT: int = 53
    
    # WebSocket Listener
    WEBSOCKET_LISTENER_ENABLED: bool = False
    WEBSOCKET_LISTENER_HOST: str = "0.0.0.0"
    WEBSOCKET_LISTENER_PORT: int = 8081
    
    # Agent defaults
    DEFAULT_SLEEP_INTERVAL: int = 60  # seconds
    DEFAULT_JITTER: int = 10  # percentage
    AGENT_TIMEOUT: int = 300  # seconds before marking inactive
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/c2_server.log"
    
    # SSL/TLS
    SSL_CERT_DIR: str = "./certs"
    
    # Performance
    WORKER_COUNT: int = 4
    THREAD_POOL_SIZE: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Create required directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
os.makedirs(settings.PAYLOAD_DIR, exist_ok=True)
os.makedirs(settings.SSL_CERT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
