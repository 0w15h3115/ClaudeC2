# agent/modules/process_manager.py
import os
import signal
import psutil
import subprocess
from typing import Dict, Any, List, Optional


class ProcessManager:
    """Process management module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'list': self.list_processes,
            'kill': self.kill_process,
            'create': self.create_process,
            'suspend': self.suspend_process,
            'resume': self.resume_process,
            'tree': self.process_tree,
            'info': self.process_info,
            'connections': self.process_connections,
            'memory': self.memory_info,
            'cpu': self.cpu_info
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute process command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def list_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List running processes"""
        filter_name = params.get('name')
        filter_user = params.get('user')
        sort_by = params.get('sort_by', 'cpu_percent')
        limit = params.get('limit', 100)
        
        processes = []
        
        # Get system stats first
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        
        stats = {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': memory.percent,
            'disk': psutil.disk_usage('/').percent,
            'process_count': 0
        }
        
        # Collect process information
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                       'memory_percent', 'status', 'create_time',
                                       'num_threads', 'cmdline']):
            try:
                info = proc.info
                
                # Apply filters
                if filter_name and filter_name.lower() not in info['name'].lower():
                    continue
                
                if filter_user and info['username'] != filter_user:
                    continue
                
                # Get command line
                cmdline = ' '.join(info['cmdline']) if info['cmdline'] else info['name']
                
                # Get parent PID
                try:
                    ppid = proc.ppid()
                except:
                    ppid = None
                
                # Get working directory
                try:
                    cwd = proc.cwd()
                except:
                    cwd = None
                
                processes.append({
                    'pid': info['pid'],
                    'ppid': ppid,
                    'name': info['name'],
                    'user': info['username'],
                    'cpu': round(info['cpu_percent'], 1),
                    'memory': round(info['memory_percent'], 1),
                    'status': info['status'],
                    'threads': info['num_threads'],
                    'cmdline': cmdline,
                    'cwd': cwd
                })
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort processes
        if sort_by in ['cpu', 'memory']:
            processes.sort(key=lambda x: x[sort_by], reverse=True)
        elif sort_by == 'name':
            processes.sort(key=lambda x: x['name'].lower())
        elif sort_by == 'pid':
            processes.sort(key=lambda x: x['pid'])
        
        # Apply limit
        processes = processes[:limit]
        
        stats['process_count'] = len(processes)
        
        return {
            'stats': stats,
            'processes': processes
        }
    
    def kill_process(self, params: Dict[str, Any]) -> str:
        """Kill a process"""
        pid = params.get('pid')
        signal_type = params.get('signal', 'SIGTERM')
        
        if not pid:
            raise Exception("PID parameter required")
        
        try:
            proc = psutil.Process(pid)
            
            # Map signal names to signal numbers
            signal_map = {
                'SIGTERM': signal.SIGTERM,
                'SIGKILL': signal.SIGKILL,
                'SIGINT': signal.SIGINT,
                'SIGHUP': signal.SIGHUP
            }
            
            if signal_type in signal_map:
                proc.send_signal(signal_map[signal_type])
            else:
                proc.terminate()
            
            # Wait a bit and check if process is gone
            try:
                proc.wait(timeout=3)
                return f"Process {pid} terminated successfully"
            except psutil.TimeoutExpired:
                # Force kill if still running
                proc.kill()
                return f"Process {pid} force killed"
                
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except psutil.AccessDenied:
            raise Exception(f"Access denied to kill process {pid}")
    
    def create_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new process"""
        command = params.get('command')
        args = params.get('args', [])
        shell = params.get('shell', False)
        background = params.get('background', True)
        env = params.get('env', {})
        cwd = params.get('cwd')
        
        if not command:
            raise Exception("Command parameter required")
        
        # Prepare command
        if shell:
            cmd = command
        else:
            cmd = [command] + args
        
        # Merge environment variables
        process_env = os.environ.copy()
        process_env.update(env)
        
        try:
            if background:
                # Start process in background
                if os.name == 'nt':
                    # Windows
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    DETACHED_PROCESS = 0x00000008
                    
                    proc = subprocess.Popen(
                        cmd,
                        shell=shell,
                        env=process_env,
                        cwd=cwd,
                        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                else:
                    # Unix/Linux
                    proc = subprocess.Popen(
                        cmd,
                        shell=shell,
                        env=process_env,
                        cwd=cwd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        preexec_fn=os.setsid
                    )
                
                return {
                    'pid': proc.pid,
                    'command': command,
                    'background': True
                }
            else:
                # Run and wait for completion
                result = subprocess.run(
                    cmd,
                    shell=shell,
                    env=process_env,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=params.get('timeout', 30)
                )
                
                return {
                    'pid': result.returncode,
                    'command': command,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'background': False
                }
                
        except subprocess.TimeoutExpired:
            raise Exception("Process timed out")
        except Exception as e:
            raise Exception(f"Failed to create process: {e}")
    
    def suspend_process(self, params: Dict[str, Any]) -> str:
        """Suspend a process"""
        pid = params.get('pid')
        if not pid:
            raise Exception("PID parameter required")
        
        try:
            proc = psutil.Process(pid)
            proc.suspend()
            return f"Process {pid} suspended"
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except psutil.AccessDenied:
            raise Exception(f"Access denied to suspend process {pid}")
    
    def resume_process(self, params: Dict[str, Any]) -> str:
        """Resume a suspended process"""
        pid = params.get('pid')
        if not pid:
            raise Exception("PID parameter required")
        
        try:
            proc = psutil.Process(pid)
            proc.resume()
            return f"Process {pid} resumed"
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except psutil.AccessDenied:
            raise Exception(f"Access denied to resume process {pid}")
    
    def process_tree(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get process tree"""
        root_pid = params.get('pid', 1)
        
        def get_children(pid):
            children = []
            try:
                parent = psutil.Process(pid)
                for child in parent.children(recursive=True):
                    try:
                        children.append({
                            'pid': child.pid,
                            'name': child.name(),
                            'status': child.status(),
                            'parent': pid
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            return children
        
        tree = []
        try:
            root = psutil.Process(root_pid)
            tree.append({
                'pid': root.pid,
                'name': root.name(),
                'status': root.status(),
                'parent': None
            })
            tree.extend(get_children(root_pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return tree
    
    def process_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed process information"""
        pid = params.get('pid')
        if not pid:
            raise Exception("PID parameter required")
        
        try:
            proc = psutil.Process(pid)
            
            # Get process info
            with proc.oneshot():
                info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'exe': proc.exe() if hasattr(proc, 'exe') else None,
                    'cmdline': proc.cmdline(),
                    'status': proc.status(),
                    'username': proc.username(),
                    'create_time': proc.create_time(),
                    'cwd': proc.cwd() if hasattr(proc, 'cwd') else None,
                    'nice': proc.nice() if hasattr(proc, 'nice') else None,
                    'num_threads': proc.num_threads(),
                    'cpu_times': proc.cpu_times()._asdict(),
                    'cpu_percent': proc.cpu_percent(interval=0.1),
                    'memory_info': proc.memory_info()._asdict(),
                    'memory_percent': proc.memory_percent()
                }
                
                # Get open files
                try:
                    info['open_files'] = [f._asdict() for f in proc.open_files()]
                except:
                    info['open_files'] = []
                
                # Get connections
                try:
                    info['connections'] = [c._asdict() for c in proc.connections()]
                except:
                    info['connections'] = []
                
                # Get environment
                try:
                    info['environ'] = proc.environ()
                except:
                    info['environ'] = {}
            
            return info
            
        except psutil.NoSuchProcess:
            raise Exception(f"Process {pid} not found")
        except psutil.AccessDenied:
            raise Exception(f"Access denied to process {pid}")
    
    def process_connections(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get process network connections"""
        pid = params.get('pid')
        
        connections = []
        
        if pid:
            # Get connections for specific process
            try:
                proc = psutil.Process(pid)
                for conn in proc.connections():
                    connections.append({
                        'pid': pid,
                        'fd': conn.fd,
                        'family': conn.family.name,
                        'type': conn.type.name,
                        'laddr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        'raddr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        'status': conn.status
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        else:
            # Get all connections
            for conn in psutil.net_connections():
                try:
                    proc_name = psutil.Process(conn.pid).name() if conn.pid else "System"
                except:
                    proc_name = "Unknown"
                
                connections.append({
                    'pid': conn.pid,
                    'process': proc_name,
                    'family': conn.family.name,
                    'type': conn.type.name,
                    'laddr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'raddr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status
                })
        
        return connections
    
    def memory_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get system memory information"""
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'virtual': {
                'total': virtual.total,
                'available': virtual.available,
                'percent': virtual.percent,
                'used': virtual.used,
                'free': virtual.free,
                'active': getattr(virtual, 'active', None),
                'inactive': getattr(virtual, 'inactive', None),
                'buffers': getattr(virtual, 'buffers', None),
                'cached': getattr(virtual, 'cached', None),
                'shared': getattr(virtual, 'shared', None)
            },
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent,
                'sin': swap.sin,
                'sout': swap.sout
            }
        }
    
    def cpu_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get CPU information"""
        interval = params.get('interval', 1)
        
        # Get CPU times
        cpu_times = psutil.cpu_times()
        
        # Get per-CPU usage
        per_cpu = psutil.cpu_percent(interval=interval, percpu=True)
        
        # Get CPU frequency
        try:
            cpu_freq = psutil.cpu_freq()
            freq = {
                'current': cpu_freq.current,
                'min': cpu_freq.min,
                'max': cpu_freq.max
            }
        except:
            freq = None
        
        # Get CPU stats
        try:
            cpu_stats = psutil.cpu_stats()
            stats = {
                'ctx_switches': cpu_stats.ctx_switches,
                'interrupts': cpu_stats.interrupts,
                'soft_interrupts': cpu_stats.soft_interrupts,
                'syscalls': getattr(cpu_stats, 'syscalls', None)
            }
        except:
            stats = None
        
        return {
            'count': psutil.cpu_count(),
            'count_logical': psutil.cpu_count(logical=True),
            'percent': psutil.cpu_percent(interval=interval),
            'percent_per_cpu': per_cpu,
            'times': {
                'user': cpu_times.user,
                'system': cpu_times.system,
                'idle': cpu_times.idle,
                'nice': getattr(cpu_times, 'nice', None),
                'iowait': getattr(cpu_times, 'iowait', None),
                'irq': getattr(cpu_times, 'irq', None),
                'softirq': getattr(cpu_times, 'softirq', None)
            },
            'frequency': freq,
            'stats': stats
        }
