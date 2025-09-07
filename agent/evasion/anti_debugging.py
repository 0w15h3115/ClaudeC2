"""
Anti-debugging techniques
"""

import os
import sys
import ctypes
import platform
import time

class AntiDebugging:
    """Anti-debugging detection and evasion"""
    
    @staticmethod
    def is_debugger_present() -> bool:
        """Check if debugger is attached"""
        if platform.system() == "Windows":
            return AntiDebugging._windows_debugger_check()
        elif platform.system() == "Linux":
            return AntiDebugging._linux_debugger_check()
        elif platform.system() == "Darwin":
            return AntiDebugging._macos_debugger_check()
        return False
    
    @staticmethod
    def _windows_debugger_check() -> bool:
        """Windows debugger detection"""
        try:
            # IsDebuggerPresent
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                return True
            
            # CheckRemoteDebuggerPresent
            is_debugged = ctypes.c_bool(False)
            kernel32.CheckRemoteDebuggerPresent(
                kernel32.GetCurrentProcess(),
                ctypes.byref(is_debugged)
            )
            if is_debugged.value:
                return True
            
            # NtGlobalFlag check
            peb = ctypes.c_ulonglong()
            process = kernel32.GetCurrentProcess()
            ntdll = ctypes.windll.ntdll
            ntdll.NtQueryInformationProcess(
                process, 0, ctypes.byref(peb), 
                ctypes.sizeof(peb), None
            )
            if peb.value & 0x70:  # FLG_HEAP_ENABLE_TAIL_CHECK | FLG_HEAP_ENABLE_FREE_CHECK | FLG_HEAP_VALIDATE_PARAMETERS
                return True
                
        except:
            pass
        return False
    
    @staticmethod
    def _linux_debugger_check() -> bool:
        """Linux debugger detection"""
        try:
            # Check /proc/self/status for TracerPid
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('TracerPid:'):
                        tracer_pid = int(line.split()[1])
                        if tracer_pid != 0:
                            return True
            
            # Check for common debuggers in parent process
            ppid = os.getppid()
            with open(f'/proc/{ppid}/cmdline', 'r') as f:
                cmdline = f.read().lower()
                debuggers = ['gdb', 'lldb', 'strace', 'ltrace']
                for debugger in debuggers:
                    if debugger in cmdline:
                        return True
                        
        except:
            pass
        return False
    
    @staticmethod
    def _macos_debugger_check() -> bool:
        """macOS debugger detection"""
        try:
            # P_TRACED flag check
            import subprocess
            result = subprocess.run(
                ['sysctl', 'kern.proc.pid.' + str(os.getpid())],
                capture_output=True,
                text=True
            )
            if 'P_TRACED' in result.stdout:
                return True
                
        except:
            pass
        return False
    
    @staticmethod
    def timing_check(threshold: float = 0.1) -> bool:
        """Detect debugging through timing analysis"""
        start = time.time()
        
        # Perform simple operation
        result = 0
        for i in range(1000):
            result += i * i
        
        elapsed = time.time() - start
        
        # If operation took too long, might be stepping through debugger
        return elapsed > threshold
