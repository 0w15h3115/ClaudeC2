"""
Sandbox detection techniques
"""

import os
import platform
import subprocess
import socket
import time
from typing import List, Dict, Any

class SandboxDetection:
    """Detect common sandbox environments"""
    
    def __init__(self):
        self.checks = {
            'vm_artifacts': self.check_vm_artifacts,
            'timing': self.check_timing_anomalies,
            'network': self.check_network_artifacts,
            'processes': self.check_sandbox_processes,
            'files': self.check_sandbox_files,
            'registry': self.check_registry_artifacts,
            'hardware': self.check_hardware_specs
        }
    
    def is_sandbox(self, checks_to_run: List[str] = None) -> bool:
        """Run sandbox detection checks"""
        if not checks_to_run:
            checks_to_run = list(self.checks.keys())
        
        for check_name in checks_to_run:
            if check_name in self.checks:
                try:
                    if self.checks[check_name]():
                        return True
                except:
                    continue
        
        return False
    
    def check_vm_artifacts(self) -> bool:
        """Check for VM artifacts"""
        if platform.system() == "Windows":
            # Check for VM drivers
            vm_files = [
                r"C:\Windows\System32\drivers\VBoxGuest.sys",
                r"C:\Windows\System32\drivers\VBoxMouse.sys",
                r"C:\Windows\System32\drivers\VBoxSF.sys",
                r"C:\Windows\System32\drivers\VBoxVideo.sys",
                r"C:\Windows\System32\drivers\vmci.sys",
                r"C:\Windows\System32\drivers\vmmouse.sys",
                r"C:\Windows\System32\drivers\vmhgfs.sys",
                r"C:\Windows\System32\drivers\vboxguest.sys"
            ]
            
            for file in vm_files:
                if os.path.exists(file):
                    return True
            
            # Check for VM processes
            try:
                output = subprocess.check_output("tasklist", shell=True).decode()
                vm_processes = ["VBoxService", "VBoxTray", "VMwareTray", "VMwareUser"]
                for proc in vm_processes:
                    if proc.lower() in output.lower():
                        return True
            except:
                pass
        
        return False
    
    def check_timing_anomalies(self) -> bool:
        """Check for timing anomalies indicating analysis"""
        # Sleep detection
        start = time.time()
        time.sleep(0.1)
        elapsed = time.time() - start
        
        # If sleep was skipped (common in sandboxes)
        if elapsed < 0.09:
            return True
        
        return False
    
    def check_network_artifacts(self) -> bool:
        """Check for sandbox network artifacts"""
        try:
            hostname = socket.gethostname().lower()
            
            # Common sandbox hostnames
            sandbox_names = [
                'sandbox', 'vmware', 'virtualbox', 'vbox', 'qemu',
                'xen', 'analysis', 'malware', 'virus', 'sample'
            ]
            
            for name in sandbox_names:
                if name in hostname:
                    return True
            
            # Check for common sandbox IPs
            ip = socket.gethostbyname(hostname)
            if ip.startswith(('10.0.0.', '192.168.56.', '192.168.122.')):
                return True
                
        except:
            pass
        
        return False
    
    def check_sandbox_processes(self) -> bool:
        """Check for common sandbox processes"""
        sandbox_procs = [
            'wireshark', 'tcpdump', 'fiddler', 'procmon', 'procexp',
            'ida', 'x64dbg', 'ollydbg', 'windbg', 'immunity',
            'sandboxie', 'cuckoomon', 'python.exe', 'perl.exe'
        ]
        
        if platform.system() == "Windows":
            try:
                output = subprocess.check_output("tasklist", shell=True).decode().lower()
                for proc in sandbox_procs:
                    if proc in output:
                        return True
            except:
                pass
        
        elif platform.system() in ["Linux", "Darwin"]:
            try:
                output = subprocess.check_output("ps aux", shell=True).decode().lower()
                for proc in sandbox_procs:
                    if proc in output:
                        return True
            except:
                pass
        
        return False
    
    def check_sandbox_files(self) -> bool:
        """Check for sandbox-related files"""
        # Common paths that indicate sandbox
        sandbox_paths = [
            '/tmp/cuckoo',
            'C:\\analysis',
            'C:\\sandbox',
            'C:\\cuckoo',
            'C:\\inetsim',
            'C:\\tools\\',
            'C:\\sample.exe'
        ]
        
        for path in sandbox_paths:
            if os.path.exists(path):
                return True
        
        return False
    
    def check_registry_artifacts(self) -> bool:
        """Check Windows registry for sandbox artifacts"""
        if platform.system() != "Windows":
            return False
        
        try:
            import winreg
            
            # Check for VMware
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\VMware, Inc.\VMware Tools")
                winreg.CloseKey(key)
                return True
            except:
                pass
            
            # Check for VirtualBox
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Oracle\VirtualBox Guest Additions")
                winreg.CloseKey(key)
                return True
            except:
                pass
                
        except ImportError:
            pass
        
        return False
    
    def check_hardware_specs(self) -> bool:
        """Check hardware specifications"""
        try:
            # Check CPU count
            cpu_count = os.cpu_count()
            if cpu_count and cpu_count < 2:
                return True
            
            # Check RAM (sandboxes often have low RAM)
            if platform.system() == "Windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', c_ulonglong),
                        ('ullAvailPhys', c_ulonglong),
                        ('ullTotalPageFile', c_ulonglong),
                        ('ullAvailPageFile', c_ulonglong),
                        ('ullTotalVirtual', c_ulonglong),
                        ('ullAvailVirtual', c_ulonglong),
                        ('ullAvailExtendedVirtual', c_ulonglong),
                    ]
                
                memoryStatus = MEMORYSTATUSEX()
                memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
                
                # Less than 2GB RAM might indicate sandbox
                if memoryStatus.ullTotalPhys < (2 * 1024 * 1024 * 1024):
                    return True
                    
        except:
            pass
        
        return False
