# agent/core/__init__.py
"""
C2 Agent Core Module
"""

from .agent import Agent
from .config import AgentConfig
from .crypto import CryptoManager
from .communications import CommunicationManager

__version__ = "1.0.0"
__all__ = ["Agent", "AgentConfig", "CryptoManager", "CommunicationManager"]
