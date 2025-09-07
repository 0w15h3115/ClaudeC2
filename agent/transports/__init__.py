"""
Agent transport modules
"""

from .http import HTTPTransport
try:
    from .https import HTTPSTransport
except ImportError:
    HTTPSTransport = None
try:
    from .dns import DNSTransport
except ImportError:
    DNSTransport = None
try:
    from .websocket import WebSocketTransport
except ImportError:
    WebSocketTransport = None

__all__ = [
    "HTTPTransport",
]

if HTTPSTransport:
    __all__.append("HTTPSTransport")
if DNSTransport:
    __all__.append("DNSTransport")
if WebSocketTransport:
    __all__.append("WebSocketTransport")