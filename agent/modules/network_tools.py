# agent/modules/network_tools.py
import os
import socket
import struct
import subprocess
import platform
import psutil
import ipaddress
from typing import Dict, Any, List, Optional, Tuple


class NetworkTools:
    """Network tools and utilities module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'interfaces': self.list_interfaces,
            'connections': self.list_connections,
            'routes': self.list_routes,
            'arp': self.arp_table,
            'dns': self.dns_lookup,
            'ping': self.ping,
            'traceroute': self.traceroute,
            'portscan': self.port_scan,
            'netstat': self.netstat,
            'hosts': self.list_hosts,
            'forward': self.port_forward
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute network command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def list_interfaces(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List network interfaces"""
        interfaces = []
        
        for name, addrs in psutil.net_if_addrs().items():
            # Get interface stats
            stats = psutil.net_if_stats().get(name)
            
            interface = {
                'name': name,
                'status': 'up' if stats and stats.isup else 'down',
                'mtu': stats.mtu if stats else None,
                'addresses': []
            }
            
            for addr in addrs:
                addr_info = {
                    'family': addr.family.name,
                    'address': addr.address
                }
                
                if addr.family == socket.AF_INET:  # IPv4
                    addr_info['netmask'] = addr.netmask
                    addr_info['broadcast'] = addr.broadcast
                    interface['ipv4'] = addr.address
                elif addr.family == socket.AF_INET6:  # IPv6
                    addr_info['netmask'] = addr.netmask
                    interface['ipv6'] = addr.address
                elif addr.family == psutil.AF_LINK:  # MAC
                    interface['mac'] = addr.address
                
                interface['addresses'].append(addr_info)
            
            interfaces.append(interface)
        
        return interfaces
    
    def list_connections(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List network connections"""
        kind = params.get('kind', 'inet')  # inet, inet4, inet6, tcp, tcp4, tcp6, udp, udp4, udp6
        state = params.get('state')  # ESTABLISHED, LISTEN, etc.
        
        connections = []
        
        for conn in psutil.net_connections(kind=kind):
            # Filter by state if specified
            if state and conn.status != state:
                continue
            
            # Get process name
            try:
                if conn.pid:
                    process = psutil.Process(conn.pid).name()
                else:
                    process = 'System'
            except:
                process = 'Unknown'
            
            conn_info = {
                'protocol': 'tcp' if conn.type == socket.SOCK_STREAM else 'udp',
                'localAddr': conn.laddr.ip if conn.laddr else '',
                'localPort': conn.laddr.port if conn.laddr else 0,
                'remoteAddr': conn.raddr.ip if conn.raddr else '',
                'remotePort': conn.raddr.port if conn.raddr else 0,
                'state': conn.status,
                'pid': conn.pid,
                'process': process
            }
            
            connections.append(conn_info)
        
        return connections
    
    def list_routes(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List routing table"""
        routes = []
        
        if platform.system() == 'Windows':
            # Windows route table
            try:
                output = subprocess.check_output(['route', 'print'], text=True)
                # Parse Windows route output
                in_ipv4_table = False
                
                for line in output.split('\n'):
                    if 'IPv4 Route Table' in line:
                        in_ipv4_table = True
                        continue
                    
                    if in_ipv4_table and line.strip():
                        parts = line.split()
                        if len(parts) >= 5 and parts[0][0].isdigit():
                            routes.append({
                                'destination': parts[0],
                                'netmask': parts[1],
                                'gateway': parts[2],
                                'interface': parts[3],
                                'metric': parts[4] if len(parts) > 4 else '0'
                            })
            except:
                pass
        else:
            # Unix/Linux route table
            try:
                with open('/proc/net/route', 'r') as f:
                    lines = f.readlines()[1:]  # Skip header
                    
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 8:
                            dest = socket.inet_ntoa(struct.pack('<I', int(parts[1], 16)))
                            gateway = socket.inet_ntoa(struct.pack('<I', int(parts[2], 16)))
                            mask = socket.inet_ntoa(struct.pack('<I', int(parts[7], 16)))
                            
                            routes.append({
                                'destination': dest,
                                'gateway': gateway,
                                'netmask': mask,
                                'interface': parts[0],
                                'metric': parts[6]
                            })
            except:
                # Fallback to netstat
                try:
                    output = subprocess.check_output(['netstat', '-rn'], text=True)
                    # Parse netstat output
                    for line in output.split('\n'):
                        parts = line.split()
                        if len(parts) >= 4 and parts[0][0].isdigit():
                            routes.append({
                                'destination': parts[0],
                                'gateway': parts[1],
                                'netmask': parts[2] if len(parts) > 4 else '255.255.255.255',
                                'interface': parts[-1],
                                'metric': '0'
                            })
                except:
                    pass
        
        return routes
    
    def arp_table(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get ARP table"""
        arp_entries = []
        
        if platform.system() == 'Windows':
            try:
                output = subprocess.check_output(['arp', '-a'], text=True)
                
                for line in output.split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[0][0].isdigit():
                        arp_entries.append({
                            'ip': parts[0],
                            'mac': parts[1],
                            'type': parts[2] if len(parts) > 2 else 'dynamic',
                            'interface': ''
                        })
            except:
                pass
        else:
            try:
                # Try /proc/net/arp first
                with open('/proc/net/arp', 'r') as f:
                    lines = f.readlines()[1:]  # Skip header
                    
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 6:
                            arp_entries.append({
                                'ip': parts[0],
                                'mac': parts[3],
                                'type': 'dynamic' if int(parts[2], 16) & 2 else 'static',
                                'interface': parts[5]
                            })
            except:
                # Fallback to arp command
                try:
                    output = subprocess.check_output(['arp', '-an'], text=True)
                    
                    for line in output.split('\n'):
                        if '(' in line and ')' in line:
                            # Parse format: hostname (IP) at MAC [ether] on interface
                            import re
                            match = re.search(r'\(([^)]+)\) at ([0-9a-fA-F:]+)', line)
                            if match:
                                arp_entries.append({
                                    'ip': match.group(1),
                                    'mac': match.group(2),
                                    'type': 'dynamic',
                                    'interface': line.split()[-1] if ' on ' in line else ''
                                })
                except:
                    pass
        
        return arp_entries
    
    def dns_lookup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform DNS lookup"""
        hostname = params.get('hostname')
        record_type = params.get('type', 'A')
        
        if not hostname:
            raise Exception("Hostname parameter required")
        
        results = {
            'hostname': hostname,
            'records': []
        }
        
        try:
            # Get IP addresses
            if record_type in ['A', 'AAAA', 'ANY']:
                try:
                    # Get all address info
                    addr_info = socket.getaddrinfo(hostname, None)
                    
                    for family, _, _, _, sockaddr in addr_info:
                        ip = sockaddr[0]
                        
                        if family == socket.AF_INET and record_type in ['A', 'ANY']:
                            results['records'].append({
                                'type': 'A',
                                'value': ip
                            })
                        elif family == socket.AF_INET6 and record_type in ['AAAA', 'ANY']:
                            results['records'].append({
                                'type': 'AAAA',
                                'value': ip
                            })
                except socket.gaierror:
                    pass
            
            # Get hostname from IP (PTR)
            if record_type in ['PTR', 'ANY']:
                try:
                    # Check if input is an IP
                    socket.inet_aton(hostname)
                    host, _, _ = socket.gethostbyaddr(hostname)
                    results['records'].append({
                        'type': 'PTR',
                        'value': host
                    })
                except:
                    pass
            
            # Get MX records (requires dig/nslookup)
            if record_type in ['MX', 'ANY']:
                try:
                    if platform.system() == 'Windows':
                        cmd = ['nslookup', '-type=mx', hostname]
                    else:
                        cmd = ['dig', '+short', 'MX', hostname]
                    
                    output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                    
                    for line in output.strip().split('\n'):
                        if line and line.startswith('"'):
                            results['records'].append({
                                'type': 'TXT',
                                'value': line.strip('"')
                            })
                except:
                    pass
            
            return results
            
        except Exception as e:
            raise Exception(f"DNS lookup failed: {e}")
    
    def ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ping a host"""
        host = params.get('host')
        count = params.get('count', 4)
        timeout = params.get('timeout', 5)
        
        if not host:
            raise Exception("Host parameter required")
        
        # Construct ping command
        if platform.system() == 'Windows':
            cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), host]
        else:
            cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        
        try:
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
            
            # Parse ping output
            lines = output.strip().split('\n')
            
            # Extract statistics
            stats = {
                'host': host,
                'sent': count,
                'received': 0,
                'lost': 0,
                'min': 0,
                'avg': 0,
                'max': 0,
                'output': output
            }
            
            # Parse statistics line
            for line in lines:
                if 'packets transmitted' in line or 'Packets: Sent' in line:
                    import re
                    # Unix: X packets transmitted, Y received
                    # Windows: Packets: Sent = X, Received = Y
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 2:
                        stats['sent'] = int(numbers[0])
                        stats['received'] = int(numbers[1])
                        stats['lost'] = stats['sent'] - stats['received']
                
                elif 'min/avg/max' in line or 'Minimum/Maximum/Average' in line:
                    import re
                    # Extract RTT values
                    numbers = re.findall(r'[\d.]+', line)
                    if len(numbers) >= 3:
                        stats['min'] = float(numbers[0])
                        stats['avg'] = float(numbers[1]) if len(numbers) > 1 else 0
                        stats['max'] = float(numbers[2]) if len(numbers) > 2 else 0
            
            stats['success'] = stats['received'] > 0
            return stats
            
        except subprocess.CalledProcessError as e:
            # Ping failed (host unreachable)
            return {
                'host': host,
                'sent': count,
                'received': 0,
                'lost': count,
                'success': False,
                'error': 'Host unreachable',
                'output': e.output if hasattr(e, 'output') else str(e)
            }
        except Exception as e:
            raise Exception(f"Ping failed: {e}")
    
    def traceroute(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Traceroute to a host"""
        host = params.get('host')
        max_hops = params.get('max_hops', 30)
        timeout = params.get('timeout', 5)
        
        if not host:
            raise Exception("Host parameter required")
        
        hops = []
        
        # Construct traceroute command
        if platform.system() == 'Windows':
            cmd = ['tracert', '-h', str(max_hops), '-w', str(timeout * 1000), host]
        else:
            cmd = ['traceroute', '-m', str(max_hops), '-w', str(timeout), host]
        
        try:
            # Run traceroute
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            hop_num = 0
            for line in proc.stdout:
                line = line.strip()
                
                # Skip header lines
                if not line or 'traceroute' in line.lower() or 'tracing' in line.lower():
                    continue
                
                # Parse hop line
                import re
                
                # Look for hop number at start of line
                match = re.match(r'^\s*(\d+)', line)
                if match:
                    hop_num = int(match.group(1))
                    
                    # Extract IPs and RTTs from line
                    ip_pattern = r'(\d+\.\d+\.\d+\.\d+)'
                    rtt_pattern = r'([\d.]+)\s*ms'
                    
                    ips = re.findall(ip_pattern, line)
                    rtts = re.findall(rtt_pattern, line)
                    
                    hop = {
                        'hop': hop_num,
                        'ip': ips[0] if ips else None,
                        'hostname': None,
                        'rtts': [float(rtt) for rtt in rtts],
                        'timeout': '*' in line
                    }
                    
                    # Try to get hostname
                    if hop['ip']:
                        try:
                            hostname, _, _ = socket.gethostbyaddr(hop['ip'])
                            hop['hostname'] = hostname
                        except:
                            pass
                    
                    hops.append(hop)
            
            proc.wait()
            return hops
            
        except Exception as e:
            raise Exception(f"Traceroute failed: {e}")
    
    def port_scan(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan ports on a host"""
        host = params.get('target')
        ports = params.get('ports', '1-1000')
        timeout = params.get('timeout', 0.5)
        
        if not host:
            raise Exception("Target parameter required")
        
        # Parse port range
        port_list = []
        if isinstance(ports, str):
            if '-' in ports:
                # Range: "1-100"
                start, end = map(int, ports.split('-'))
                port_list = range(start, end + 1)
            elif ',' in ports:
                # List: "80,443,8080"
                port_list = [int(p.strip()) for p in ports.split(',')]
            else:
                # Single port
                port_list = [int(ports)]
        elif isinstance(ports, list):
            port_list = ports
        else:
            port_list = [ports]
        
        # Limit number of ports to scan
        max_ports = 1000
        if len(port_list) > max_ports:
            port_list = list(port_list)[:max_ports]
        
        results = []
        
        # Resolve hostname to IP
        try:
            target_ip = socket.gethostbyname(host)
        except socket.gaierror:
            raise Exception(f"Cannot resolve hostname: {host}")
        
        # Scan ports
        for port in port_list:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = {
                'port': port,
                'open': False,
                'service': self._get_service_name(port)
            }
            
            try:
                # Attempt connection
                sock.connect((target_ip, port))
                result['open'] = True
                
                # Try to grab banner
                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(1024).decode('utf-8', errors='ignore')
                    if banner:
                        result['banner'] = banner.strip()
                except:
                    pass
                
            except (socket.timeout, socket.error):
                pass
            finally:
                sock.close()
            
            results.append(result)
        
        return results
    
    def _get_service_name(self, port: int) -> str:
        """Get common service name for port"""
        common_ports = {
            21: 'FTP',
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            143: 'IMAP',
            443: 'HTTPS',
            445: 'SMB',
            3306: 'MySQL',
            3389: 'RDP',
            5432: 'PostgreSQL',
            5900: 'VNC',
            8080: 'HTTP-Alt',
            8443: 'HTTPS-Alt'
        }
        
        return common_ports.get(port, 'Unknown')
    
    def netstat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get network statistics"""
        stats = {}
        
        # Get interface statistics
        net_io = psutil.net_io_counters(pernic=True)
        
        stats['interfaces'] = {}
        for name, counters in net_io.items():
            stats['interfaces'][name] = {
                'bytes_sent': counters.bytes_sent,
                'bytes_recv': counters.bytes_recv,
                'packets_sent': counters.packets_sent,
                'packets_recv': counters.packets_recv,
                'errors_in': counters.errin,
                'errors_out': counters.errout,
                'drops_in': counters.dropin,
                'drops_out': counters.dropout
            }
        
        # Get global statistics
        global_io = psutil.net_io_counters()
        stats['global'] = {
            'bytes_sent': global_io.bytes_sent,
            'bytes_recv': global_io.bytes_recv,
            'packets_sent': global_io.packets_sent,
            'packets_recv': global_io.packets_recv
        }
        
        # Get connection statistics by state
        conn_stats = {}
        for conn in psutil.net_connections():
            state = conn.status
            if state not in conn_stats:
                conn_stats[state] = 0
            conn_stats[state] += 1
        
        stats['connections'] = conn_stats
        
        return stats
    
    def list_hosts(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List hosts on local network"""
        subnet = params.get('subnet')
        
        if not subnet:
            # Try to determine local subnet
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                        # Calculate subnet from IP and netmask
                        try:
                            network = ipaddress.ip_network(f"{addr.address}/{addr.netmask}", strict=False)
                            subnet = str(network)
                            break
                        except:
                            continue
                if subnet:
                    break
        
        if not subnet:
            raise Exception("Could not determine local subnet")
        
        hosts = []
        
        try:
            network = ipaddress.ip_network(subnet)
            
            # Limit scan to /24 or smaller
            if network.num_addresses > 256:
                raise Exception("Subnet too large (max /24)")
            
            # Ping sweep
            for ip in network.hosts():
                ip_str = str(ip)
                
                # Quick ping check
                if platform.system() == 'Windows':
                    cmd = ['ping', '-n', '1', '-w', '100', ip_str]
                else:
                    cmd = ['ping', '-c', '1', '-W', '1', ip_str]
                
                try:
                    subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                    
                    # Host is up, get hostname
                    try:
                        hostname, _, _ = socket.gethostbyaddr(ip_str)
                    except:
                        hostname = None
                    
                    # Get MAC address from ARP
                    mac = None
                    for arp_entry in self.arp_table({}):
                        if arp_entry['ip'] == ip_str:
                            mac = arp_entry['mac']
                            break
                    
                    hosts.append({
                        'ip': ip_str,
                        'hostname': hostname,
                        'mac': mac,
                        'alive': True
                    })
                    
                except subprocess.CalledProcessError:
                    pass
            
            return hosts
            
        except Exception as e:
            raise Exception(f"Host discovery failed: {e}")
    
    def port_forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set up port forwarding (placeholder)"""
        # This would require more complex implementation
        # involving raw sockets or iptables manipulation
        raise Exception("Port forwarding not implemented in this version"):
                        if line and not line.startswith(';'):
                            parts = line.split()
                            if len(parts) >= 2:
                                results['records'].append({
                                    'type': 'MX',
                                    'priority': parts[0],
                                    'value': parts[1].rstrip('.')
                                })
                except:
                    pass
            
            # Get TXT records
            if record_type in ['TXT', 'ANY']:
                try:
                    if platform.system() == 'Windows':
                        cmd = ['nslookup', '-type=txt', hostname]
                    else:
                        cmd = ['dig', '+short', 'TXT', hostname]
                    
                    output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                    
                    for line in output.strip().split('\n
