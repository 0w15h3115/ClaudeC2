"""
Anti-analysis techniques to evade detection and analysis
"""

import os
import sys
import time
import ctypes
import platform
import threading
import random
from typing import List, Callable

class AntiAnalysis:
    """General anti-analysis techniques"""
    
    def __init__(self):
        self.platform = platform.system()
        
    def detect_hooks(self) -> bool:
        """Detect API hooks commonly used by security tools"""
        if self.platform == "Windows":
            return self._detect_windows_hooks()
        return False
    
    def _detect_windows_hooks(self) -> bool:
        """Detect Windows API hooks"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Check common hooked functions
            functions_to_check = [
                ("kernel32.dll", "CreateProcessW"),
                ("kernel32.dll", "VirtualAlloc"),
                ("ntdll.dll", "NtCreateProcess"),
                ("ntdll.dll", "NtWriteVirtualMemory"),
                ("ws2_32.dll", "connect"),
                ("wininet.dll", "InternetOpenW")
            ]
            
            for dll_name, func_name in functions_to_check:
                try:
                    dll = ctypes.WinDLL(dll_name)
                    func = getattr(dll, func_name)
                    func_addr = ctypes.cast(func, ctypes.c_void_p).value
                    
                    # Read first few bytes
                    first_bytes = ctypes.string_at(func_addr, 5)
                    
                    # Check for common hook patterns
                    # JMP instruction (E9) or PUSH+RET (68+C3)
                    if first_bytes[0] == 0xE9 or (first_bytes[0] == 0x68 and first_bytes[4] == 0xC3):
                        return True
                        
                except:
                    continue
                    
        except:
            pass
            
        return False
    
    def environmental_keying(self, expected_values: dict) -> bool:
        """Verify environment matches expected values"""
        checks_passed = 0
        total_checks = len(expected_values)
        
        for key, expected in expected_values.items():
            actual = None
            
            if key == "hostname":
                actual = os.environ.get('COMPUTERNAME', '').lower()
            elif key == "username":
                actual = os.environ.get('USERNAME', '').lower()
            elif key == "domain":
                actual = os.environ.get('USERDOMAIN', '').lower()
            elif key == "cpu_count":
                actual = os.cpu_count()
            elif key == "platform":
                actual = platform.platform().lower()
            
            if actual and str(expected).lower() in str(actual).lower():
                checks_passed += 1
        
        # Require at least 50% of checks to pass
        return checks_passed >= (total_checks / 2)
    
    def detect_monitoring_tools(self) -> List[str]:
        """Detect running monitoring/analysis tools"""
        detected_tools = []
        
        # Process names to check
        monitoring_processes = {
            'wireshark': 'Network Analysis',
            'fiddler': 'HTTP Debugging',
            'procmon': 'Process Monitor',
            'procexp': 'Process Explorer',
            'tcpview': 'Network Monitor',
            'autoruns': 'Startup Monitor',
            'filemon': 'File Monitor',
            'regmon': 'Registry Monitor',
            'idaq': 'IDA Pro',
            'x64dbg': 'x64 Debugger',
            'ollydbg': 'OllyDbg',
            'windbg': 'WinDbg',
            'immunity': 'Immunity Debugger',
            'pestudio': 'PE Analysis',
            'lordpe': 'PE Editor',
            'sysanalyzer': 'System Analyzer',
            'sniffhit': 'API Monitor',
            'apimonitor': 'API Monitor',
            'glasswire': 'Network Monitor'
        }
        
        if self.platform == "Windows":
            try:
                import subprocess
                output = subprocess.check_output("tasklist /fo csv", shell=True).decode()
                
                for proc_name, tool_name in monitoring_processes.items():
                    if proc_name.lower() in output.lower():
                        detected_tools.append(tool_name)
                        
            except:
                pass
                
        elif self.platform in ["Linux", "Darwin"]:
            try:
                import subprocess
                output = subprocess.check_output("ps aux", shell=True).decode()
                
                for proc_name, tool_name in monitoring_processes.items():
                    if proc_name.lower() in output.lower():
                        detected_tools.append(tool_name)
                        
            except:
                pass
        
        return detected_tools
    
    def code_flow_obfuscation(self, func: Callable) -> Callable:
        """Obfuscate code flow with junk operations"""
        def wrapper(*args, **kwargs):
            # Random junk operations
            junk_ops = [
                lambda: sum([i**2 for i in range(random.randint(10, 100))]),
                lambda: ''.join([chr(i) for i in range(65, 91)]),
                lambda: [x for x in range(1000) if x % 2 == 0],
                lambda: {i: i**2 for i in range(50)}
            ]
            
            # Execute random junk operations
            for _ in range(random.randint(1, 3)):
                random.choice(junk_ops)()
            
            # Execute real function
            result = func(*args, **kwargs)
            
            # More junk operations
            for _ in range(random.randint(1, 3)):
                random.choice(junk_ops)()
            
            return result
            
        return wrapper
    
    def detect_breakpoints(self) -> bool:
        """Detect software breakpoints"""
        if self.platform == "Windows":
            try:
                # Check for int3 (0xCC) breakpoints
                import ctypes
                
                # Get current function address
                func_addr = id(self.detect_breakpoints)
                
                # Read memory at function start
                memory_content = ctypes.string_at(func_addr, 64)
                
                # Check for breakpoint instructions
                if b'\xCC' in memory_content:
                    return True
                    
            except:
                pass
                
        return False
    
    def timing_obfuscation(self, min_delay: float = 0.1, max_delay: float = 1.0):
        """Add random delays to obscure timing patterns"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def detect_virtualization(self) -> dict:
        """Comprehensive virtualization detection"""
        indicators = {
            'hypervisor': False,
            'vm_type': None,
            'confidence': 0
        }
        
        confidence = 0
        
        # CPU checks
        try:
            if self.platform == "Windows":
                import subprocess
                cpu_info = subprocess.check_output("wmic cpu get name", shell=True).decode()
                
                if any(vm in cpu_info.lower() for vm in ['virtual', 'vmware', 'vbox', 'qemu', 'xen']):
                    confidence += 30
                    
            # Check CPU features
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                    if 'hypervisor' in cpuinfo:
                        indicators['hypervisor'] = True
                        confidence += 40
            except:
                pass
                
        except:
            pass
        
        # MAC address checks
        try:
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                          for ele in range(0,8*6,8)][::-1])
            
            # Known VM MAC prefixes
            vm_macs = {
                '08:00:27': 'VirtualBox',
                '00:05:69': 'VMware',
                '00:0c:29': 'VMware',
                '00:1c:14': 'VMware',
                '00:50:56': 'VMware',
                '52:54:00': 'QEMU/KVM',
                '00:16:3e': 'Xen'
            }
            
            mac_prefix = mac[:8].lower()
            for prefix, vm_type in vm_macs.items():
                if mac_prefix == prefix.lower():
                    indicators['vm_type'] = vm_type
                    confidence += 50
                    break
                    
        except:
            pass
        
        indicators['confidence'] = min(confidence, 100)
        return indicators
    
    def memory_guard(self, data: bytes, key: int = 0x55) -> bytes:
        """Simple XOR encryption for memory strings"""
        return bytes([b ^ key for b in data])
    
    def api_hashing(self, api_name: str) -> int:
        """Hash API names to avoid static detection"""
        hash_value = 0
        for char in api_name:
            hash_value = ((hash_value << 5) + hash_value) + ord(char)
            hash_value = hash_value & 0xFFFFFFFF
        return hash_value
    
    def detect_analysis_artifacts(self) -> List[str]:
        """Detect various analysis artifacts"""
        artifacts = []
        
        # Check for analysis-related files
        analysis_files = [
            'C:\\analysis.log',
            'C:\\sample.exe',
            'C:\\malware.exe',
            '/tmp/analysis.log',
            '/tmp/sample',
            '~/Desktop/malware',
            'C:\\tools\\',
            'C:\\analysis\\'
        ]
        
        for filepath in analysis_files:
            if os.path.exists(os.path.expanduser(filepath)):
                artifacts.append(f"Analysis file: {filepath}")
        
        # Check for analysis-related environment variables
        suspicious_env_vars = ['MALWARE_', 'SANDBOX_', 'ANALYSIS_', 'CUCKOO_']
        for var in os.environ:
            for suspicious in suspicious_env_vars:
                if suspicious in var.upper():
                    artifacts.append(f"Environment variable: {var}")
        
        # Check loaded modules (Windows)
        if self.platform == "Windows":
            try:
                import ctypes
                import ctypes.wintypes
                
                # Get loaded modules
                h_process = ctypes.windll.kernel32.GetCurrentProcess()
                h_modules = (ctypes.wintypes.HMODULE * 1024)()
                cb_needed = ctypes.wintypes.DWORD()
                
                ctypes.windll.psapi.EnumProcessModules(
                    h_process,
                    ctypes.byref(h_modules),
                    ctypes.sizeof(h_modules),
                    ctypes.byref(cb_needed)
                )
                
                # Check for analysis DLLs
                analysis_dlls = ['api_log.dll', 'dir_watch.dll', 'pstorec.dll', 'vmcheck.dll']
                
                for i in range(cb_needed.value // ctypes.sizeof(ctypes.wintypes.HMODULE)):
                    module_name = ctypes.create_unicode_buffer(260)
                    ctypes.windll.kernel32.GetModuleFileNameW(
                        h_modules[i],
                        module_name,
                        ctypes.sizeof(module_name) // ctypes.sizeof(module_name[0])
                    )
                    
                    for dll in analysis_dlls:
                        if dll.lower() in module_name.value.lower():
                            artifacts.append(f"Analysis DLL: {dll}")
                            
            except:
                pass
        
        return artifacts
