# agent/modules/basic_commands.py
import os
import sys
import pwd
import grp
import platform
import subprocess
from typing import Dict, Any, List


class BasicCommands:
    """Basic command execution module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'pwd': self.pwd,
            'cd': self.cd,
            'ls': self.ls,
            'cat': self.cat,
            'whoami': self.whoami,
            'hostname': self.hostname,
            'uname': self.uname,
            'env': self.env,
            'exec': self.exec_command,
            'eval': self.eval_code,
            'sleep': self.sleep,
            'exit': self.exit
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'output': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def pwd(self, params: Dict[str, Any]) -> str:
        """Get current working directory"""
        return os.getcwd()
    
    def cd(self, params: Dict[str, Any]) -> str:
        """Change directory"""
        path = params.get('path', os.path.expanduser('~'))
        try:
            os.chdir(path)
            return f"Changed directory to: {os.getcwd()}"
        except FileNotFoundError:
            raise Exception(f"Directory not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def ls(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List directory contents"""
        path = params.get('path', '.')
        show_hidden = params.get('all', False)
        detailed = params.get('detailed', True)
        
        try:
            entries = []
            for entry in os.listdir(path):
                if not show_hidden and entry.startswith('.'):
                    continue
                
                full_path = os.path.join(path, entry)
                
                try:
                    stat = os.stat(full_path)
                    
                    if detailed:
                        # Get file details
                        is_dir = os.path.isdir(full_path)
                        
                        # Get permissions
                        mode = stat.st_mode
                        perms = self._get_permissions(mode)
                        
                        # Get owner/group (Unix only)
                        try:
                            owner = pwd.getpwuid(stat.st_uid).pw_name
                            group = grp.getgrgid(stat.st_gid).gr_name
                        except:
                            owner = str(stat.st_uid)
                            group = str(stat.st_gid)
                        
                        entries.append({
                            'name': entry,
                            'type': 'directory' if is_dir else 'file',
                            'size': stat.st_size,
                            'permissions': perms,
                            'owner': owner,
                            'group': group,
                            'modified': stat.st_mtime
                        })
                    else:
                        entries.append({
                            'name': entry,
                            'type': 'directory' if os.path.isdir(full_path) else 'file'
                        })
                except:
                    # Skip files we can't stat
                    pass
            
            return sorted(entries, key=lambda x: (x['type'] != 'directory', x['name']))
            
        except FileNotFoundError:
            raise Exception(f"Directory not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def _get_permissions(self, mode: int) -> str:
        """Convert file mode to permission string"""
        import stat
        
        perms = []
        
        # File type
        if stat.S_ISDIR(mode):
            perms.append('d')
        elif stat.S_ISLNK(mode):
            perms.append('l')
        else:
            perms.append('-')
        
        # Owner permissions
        perms.append('r' if mode & stat.S_IRUSR else '-')
        perms.append('w' if mode & stat.S_IWUSR else '-')
        perms.append('x' if mode & stat.S_IXUSR else '-')
        
        # Group permissions
        perms.append('r' if mode & stat.S_IRGRP else '-')
        perms.append('w' if mode & stat.S_IWGRP else '-')
        perms.append('x' if mode & stat.S_IXGRP else '-')
        
        # Other permissions
        perms.append('r' if mode & stat.S_IROTH else '-')
        perms.append('w' if mode & stat.S_IWOTH else '-')
        perms.append('x' if mode & stat.S_IXOTH else '-')
        
        return ''.join(perms)
    
    def cat(self, params: Dict[str, Any]) -> str:
        """Read file contents"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
                # Limit size to prevent memory issues
                max_size = params.get('max_size', 1024 * 1024)  # 1MB default
                if len(content) > max_size:
                    content = content[:max_size] + f"\n\n[Truncated - file size exceeds {max_size} bytes]"
                
                return content
                
        except FileNotFoundError:
            raise Exception(f"File not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
        except IsADirectoryError:
            raise Exception(f"Is a directory: {path}")
    
    def whoami(self, params: Dict[str, Any]) -> str:
        """Get current user"""
        return os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
    
    def hostname(self, params: Dict[str, Any]) -> str:
        """Get hostname"""
        import socket
        return socket.gethostname()
    
    def uname(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Get system information"""
        uname = platform.uname()
        return {
            'system': uname.system,
            'node': uname.node,
            'release': uname.release,
            'version': uname.version,
            'machine': uname.machine,
            'processor': uname.processor
        }
    
    def env(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Get environment variables"""
        # Filter sensitive variables
        sensitive_vars = ['PASSWORD', 'TOKEN', 'KEY', 'SECRET', 'CREDENTIAL']
        
        env_vars = {}
        for key, value in os.environ.items():
            # Check if variable name contains sensitive keywords
            is_sensitive = any(sensitive in key.upper() for sensitive in sensitive_vars)
            
            if is_sensitive and not params.get('include_sensitive', False):
                env_vars[key] = '***REDACTED***'
            else:
                env_vars[key] = value
        
        return env_vars
    
    def exec_command(self, params: Dict[str, Any]) -> str:
        """Execute shell command"""
        command = params.get('command')
        if not command:
            raise Exception("Command parameter required")
        
        # Check if command is allowed
        if not self._is_command_allowed(command):
            raise Exception("Command not allowed")
        
        return self.agent.execute_command(command)
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed"""
        # Blacklist dangerous commands
        blacklist = [
            'rm -rf /',
            'mkfs',
            'dd if=/dev/zero',
            ':(){:|:&};:',  # Fork bomb
            '> /dev/sda',
            'format c:',
        ]
        
        command_lower = command.lower().strip()
        
        for dangerous in blacklist:
            if dangerous in command_lower:
                return False
        
        return True
    
    def eval_code(self, params: Dict[str, Any]) -> Any:
        """Evaluate Python code"""
        code = params.get('code')
        if not code:
            raise Exception("Code parameter required")
        
        # Create restricted globals
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
            },
            'os': os,
            'sys': sys,
            'platform': platform,
        }
        
        try:
            # Execute code in restricted environment
            result = eval(code, restricted_globals, {})
            return str(result)
        except Exception as e:
            raise Exception(f"Eval error: {e}")
    
    def sleep(self, params: Dict[str, Any]) -> str:
        """Sleep for specified seconds"""
        import time
        
        seconds = params.get('seconds', 1)
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise Exception("Invalid seconds parameter")
        
        # Limit maximum sleep time
        max_sleep = 300  # 5 minutes
        if seconds > max_sleep:
            seconds = max_sleep
        
        time.sleep(seconds)
        return f"Slept for {seconds} seconds"
    
    def exit(self, params: Dict[str, Any]) -> str:
        """Exit agent"""
        self.agent.shutdown()
        return "Agent shutting down..."
