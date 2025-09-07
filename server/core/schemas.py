"""
Pydantic schemas for request/response validation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, constr, validator
import re

# User schemas
class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: str
    role: str = "operator"
    
    @validator('email')
    def validate_email(cls, v):
        # Basic email validation that allows .local domains
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.local$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v

class UserCreate(UserBase):
    password: constr(min_length=8)
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ["admin", "operator", "viewer"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserToken(BaseModel):
    id: str
    username: str
    email: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserToken

# Session schemas
class SessionBase(BaseModel):
    name: constr(min_length=1, max_length=100)
    description: Optional[str] = None

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SessionResponse(SessionBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    agent_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Agent schemas
class AgentCheckIn(BaseModel):
    agent_id: Optional[str] = None
    session_id: str
    hostname: str
    username: str
    platform: str
    architecture: str
    process_id: int
    internal_ip: str
    external_ip: str
    process_name: Optional[str] = None
    mac_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class AgentUpdate(BaseModel):
    sleep_interval: Optional[int] = None
    jitter: Optional[int] = None
    status: Optional[str] = None
    kill_date: Optional[datetime] = None
    working_hours: Optional[str] = None

class AgentResponse(BaseModel):
    id: str
    session_id: str
    hostname: str
    username: str
    platform: str
    architecture: str
    process_id: int
    internal_ip: str
    external_ip: str
    status: str
    last_seen: datetime
    first_seen: datetime
    sleep_interval: int
    jitter: int
    
    class Config:
        from_attributes = True

# Task schemas
class TaskCreate(BaseModel):
    command: str
    parameters: Optional[Dict[str, Any]] = {}
    priority: Optional[int] = Field(5, ge=1, le=10)

class TaskResult(BaseModel):
    task_id: str
    status: str = "completed"
    result: Optional[str] = None
    error: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    agent_id: str
    command: str
    parameters: Optional[str] = None
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]
    created_by: Optional[str]
    priority: int
    
    class Config:
        from_attributes = True

# Listener schemas
class ListenerBase(BaseModel):
    name: constr(min_length=1, max_length=100)
    type: str
    bind_address: str = "0.0.0.0"
    bind_port: int = Field(..., ge=1, le=65535)

    @validator('type')
    def validate_type(cls, v):
        allowed_types = ["http", "https", "dns", "tcp", "smb"]
        if v not in allowed_types:
            raise ValueError(f"Type must be one of {allowed_types}")
        return v

class ListenerCreate(ListenerBase):
    configuration: Optional[Dict[str, Any]] = {}
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_enabled: bool = False

class ListenerUpdate(BaseModel):
    bind_address: Optional[str] = None
    bind_port: Optional[int] = None
    configuration: Optional[Dict[str, Any]] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_enabled: Optional[bool] = None

class ListenerResponse(ListenerBase):
    id: str
    configuration: Optional[str] = None
    is_active: bool
    is_running: Optional[bool] = False
    created_at: datetime
    ssl_enabled: bool
    
    class Config:
        from_attributes = True

# Payload schemas
class PayloadCreate(BaseModel):
    name: str
    type: str
    platform: str
    architecture: str
    listener_id: str
    configuration: Dict[str, Any] = {}

class PayloadResponse(BaseModel):
    id: str
    name: str
    type: str
    platform: str
    architecture: str
    listener_id: str
    file_hash: Optional[str]
    file_size: Optional[int]
    created_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True

# Download schemas
class DownloadResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    filename: str
    file_path: str
    file_size: int
    file_hash: str
    downloaded_at: datetime
    
    class Config:
        from_attributes = True

# Credential schemas
class CredentialResponse(BaseModel):
    id: str
    agent_id: str
    type: str
    username: Optional[str]
    domain: Optional[str]
    host: Optional[str]
    service: Optional[str]
    harvested_at: datetime
    
    class Config:
        from_attributes = True

# WebSocket messages
class WSMessage(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
