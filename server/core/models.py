"""
SQLAlchemy database models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base

def generate_id():
    """Generate a unique ID"""
    return str(uuid.uuid4())

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_id)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String(20), default="operator")  # admin, operator, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    sessions = relationship("OperatorSession", back_populates="user", cascade="all, delete-orphan")
    tasks_created = relationship("Task", back_populates="creator")

class OperatorSession(Base):
    """Operation session model"""
    __tablename__ = "operator_sessions"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    agents = relationship("Agent", back_populates="session", cascade="all, delete-orphan")

class Agent(Base):
    """Agent/implant model"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, default=generate_id)
    session_id = Column(String, ForeignKey("operator_sessions.id"), nullable=False)
    
    # Agent information
    hostname = Column(String(255))
    username = Column(String(100))
    platform = Column(String(50))  # Windows, Linux, Darwin
    architecture = Column(String(20))  # x86, x64, arm64
    process_id = Column(Integer)
    process_name = Column(String(255))
    
    # Network information
    internal_ip = Column(String(45))
    external_ip = Column(String(45))
    mac_address = Column(String(17))
    
    # Agent status
    status = Column(String(20), default="active")  # active, inactive, dead, sleeping
    last_seen = Column(DateTime, server_default=func.now())
    first_seen = Column(DateTime, server_default=func.now())
    
    # Agent configuration
    sleep_interval = Column(Integer, default=60)  # seconds
    jitter = Column(Integer, default=10)  # percentage
    kill_date = Column(DateTime)
    working_hours = Column(String(100))  # JSON string
    
    # Encryption keys
    encryption_key = Column(String(255))
    
    # Additional metadata
    agent_metadata = Column(Text)  # JSON string for extensibility
    
    # Relationships
    session = relationship("OperatorSession", back_populates="agents")
    tasks = relationship("Task", back_populates="agent", cascade="all, delete-orphan")

class Task(Base):
    """Task model"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_id)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # Task details
    command = Column(String(100), nullable=False)
    parameters = Column(Text)  # JSON string
    
    # Task status
    status = Column(String(20), default="pending")  # pending, sent, completed, failed, cancelled
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    sent_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    result = Column(Text)
    error = Column(Text)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"))
    priority = Column(Integer, default=5)  # 1-10, 1 being highest
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
    creator = relationship("User", back_populates="tasks_created")

class Listener(Base):
    """Listener model"""
    __tablename__ = "listeners"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # http, https, dns, tcp, smb
    
    # Binding configuration
    bind_address = Column(String(45), default="0.0.0.0")
    bind_port = Column(Integer, nullable=False)
    
    # Listener configuration
    configuration = Column(Text)  # JSON string
    
    # Status
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # SSL/TLS configuration
    ssl_cert = Column(Text)
    ssl_key = Column(Text)
    ssl_enabled = Column(Boolean, default=False)

class Download(Base):
    """File download tracking"""
    __tablename__ = "downloads"
    
    id = Column(String, primary_key=True, default=generate_id)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # File information
    filename = Column(String(255))
    file_path = Column(Text)
    file_size = Column(Integer)
    file_hash = Column(String(64))  # SHA256
    
    # Storage
    storage_path = Column(Text)
    
    # Timestamps
    downloaded_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    task = relationship("Task")
    agent = relationship("Agent")

class Credential(Base):
    """Harvested credentials"""
    __tablename__ = "credentials"
    
    id = Column(String, primary_key=True, default=generate_id)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"))
    
    # Credential information
    type = Column(String(50))  # password, hash, token, key
    username = Column(String(255))
    password = Column(Text)  # Encrypted
    domain = Column(String(255))
    host = Column(String(255))
    service = Column(String(100))  # rdp, ssh, http, etc
    
    # Additional data
    additional_data = Column(Text)  # JSON string
    
    # Timestamps
    harvested_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    agent = relationship("Agent")
    task = relationship("Task")

class AuditLog(Base):
    """Audit log for tracking actions"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Action details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String)
    
    # Additional information
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    details = Column(Text)  # JSON string
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User")

class Payload(Base):
    """Generated payloads"""
    __tablename__ = "payloads"
    
    id = Column(String, primary_key=True, default=generate_id)
    
    # Payload information
    name = Column(String(100), nullable=False)
    type = Column(String(50))  # exe, dll, shellcode, script
    platform = Column(String(50))  # windows, linux, darwin
    architecture = Column(String(20))  # x86, x64, arm64
    
    # Configuration
    listener_id = Column(String, ForeignKey("listeners.id"))
    configuration = Column(Text)  # JSON string
    
    # Build information
    build_command = Column(Text)
    output_path = Column(Text)
    file_hash = Column(String(64))  # SHA256
    file_size = Column(Integer)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    listener = relationship("Listener")
    creator = relationship("User")
