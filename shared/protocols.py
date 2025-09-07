"""
Communication protocol definitions
"""

import json
import struct
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class MessageType(Enum):
    """Message types"""
    CHECKIN = "checkin"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    HEARTBEAT = "heartbeat"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    ERROR = "error"

@dataclass
class Message:
    """Protocol message"""
    msg_type: MessageType
    msg_id: str
    data: Dict[str, Any]
    
    def to_bytes(self) -> bytes:
        """Serialize message to bytes"""
        json_data = json.dumps({
            'type': self.msg_type.value,
            'id': self.msg_id,
            'data': self.data
        })
        
        # Add length prefix
        data_bytes = json_data.encode('utf-8')
        length = struct.pack('!I', len(data_bytes))
        return length + data_bytes
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        """Deserialize message from bytes"""
        # Extract length
        if len(data) < 4:
            raise ValueError("Invalid message: too short")
        
        length = struct.unpack('!I', data[:4])[0]
        if len(data) < 4 + length:
            raise ValueError("Invalid message: incomplete")
        
        # Extract JSON data
        json_data = data[4:4+length].decode('utf-8')
        msg_dict = json.loads(json_data)
        
        return cls(
            msg_type=MessageType(msg_dict['type']),
            msg_id=msg_dict['id'],
            data=msg_dict['data']
        )

class Protocol:
    """Communication protocol handler"""
    
    VERSION = "2.0"
    
    @staticmethod
    def create_checkin_message(agent_info: Dict[str, Any]) -> Message:
        """Create agent checkin message"""
        import uuid
        return Message(
            msg_type=MessageType.CHECKIN,
            msg_id=str(uuid.uuid4()),
            data=agent_info
        )
    
    @staticmethod
    def create_task_response(task_id: str, result: Any, error: Optional[str] = None) -> Message:
        """Create task response message"""
        import uuid
        return Message(
            msg_type=MessageType.TASK_RESPONSE,
            msg_id=str(uuid.uuid4()),
            data={
                'task_id': task_id,
                'result': result,
                'error': error,
                'status': 'failed' if error else 'completed'
            }
        )
    
    @staticmethod
    def validate_message(message: Message) -> bool:
        """Validate message format"""
        # Check required fields based on message type
        if message.msg_type == MessageType.CHECKIN:
            required = ['hostname', 'username', 'platform', 'session_id']
        elif message.msg_type == MessageType.TASK_RESPONSE:
            required = ['task_id', 'status']
        else:
            required = []
        
        for field in required:
            if field not in message.data:
                return False
        
        return True
