# agent/modules/__init__.py
"""
Agent capability modules
"""

from .basic_commands import BasicCommands
from .file_operations import FileOperations
from .process_manager import ProcessManager
from .network_tools import NetworkTools
from .persistence import Persistence
from .credentials import Credentials
from .screenshot import Screenshot
from .lateral_movement import LateralMovement

__all__ = [
    "BasicCommands",
    "FileOperations", 
    "ProcessManager",
    "NetworkTools",
    "Persistence",
    "Credentials",
    "Screenshot",
    "LateralMovement"
]
