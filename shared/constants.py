"""
Shared constants
"""

# Agent states
AGENT_STATE_ACTIVE = "active"
AGENT_STATE_INACTIVE = "inactive"
AGENT_STATE_DEAD = "dead"
AGENT_STATE_SLEEPING = "sleeping"

# Task states
TASK_STATE_PENDING = "pending"
TASK_STATE_SENT = "sent"
TASK_STATE_COMPLETED = "completed"
TASK_STATE_FAILED = "failed"
TASK_STATE_CANCELLED = "cancelled"

# Command types
CMD_SHELL = "shell"
CMD_DOWNLOAD = "download"
CMD_UPLOAD = "upload"
CMD_PS = "ps"
CMD_KILL = "kill"
CMD_PERSIST = "persist"
CMD_KEYLOG = "keylog"
CMD_SCREENSHOT = "screenshot"
CMD_PORTSCAN = "portscan"
CMD_SYSINFO = "sysinfo"
CMD_SLEEP = "sleep"
CMD_EXIT = "exit"

# Default values
DEFAULT_SLEEP_INTERVAL = 60  # seconds
DEFAULT_JITTER = 10  # percentage
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3

# Size limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_COMMAND_OUTPUT = 1024 * 1024    # 1MB
MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024  # 10MB

# Network constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DEFAULT_BIND_ADDRESS = "0.0.0.0"

# Encryption
ENCRYPTION_ALGORITHM = "AES-256-CBC"
KEY_DERIVATION_ITERATIONS = 100000
