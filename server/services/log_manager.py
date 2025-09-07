"""
Log management service for C2 operations
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
import gzip
import shutil

from core.database import SessionLocal
from core.models import AuditLog, Agent, Task, User
from core.config import settings

class LogManager:
    """Centralized logging for C2 operations"""
    
    def __init__(self):
        self.log_dir = Path(settings.LOG_FILE).parent
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup different loggers
        self.loggers = {
            'server': self._setup_logger('server', 'c2_server.log'),
            'agent': self._setup_logger('agent', 'c2_agent.log'),
            'audit': self._setup_logger('audit', 'c2_audit.log'),
            'security': self._setup_logger('security', 'c2_security.log'),
            'error': self._setup_logger('error', 'c2_error.log')
        }
        
        # Log rotation settings
        self.max_log_size = 100 * 1024 * 1024  # 100MB
        self.backup_count = 10
        self.compression_enabled = True
        
        # Start background tasks
        asyncio.create_task(self._log_maintenance_task())
    
    def _setup_logger(self, name: str, filename: str) -> logging.Logger:
        """Setup individual logger with rotation"""
        logger = logging.getLogger(f'c2.{name}')
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler for errors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_server_event(self, event_type: str, message: str, 
                        metadata: Optional[Dict[str, Any]] = None):
        """Log server events"""
        log_entry = {
            'event_type': event_type,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['server'].info(json.dumps(log_entry))
    
    def log_agent_event(self, agent_id: str, event_type: str, 
                       message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log agent-related events"""
        log_entry = {
            'agent_id': agent_id,
            'event_type': event_type,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['agent'].info(json.dumps(log_entry))
    
    def log_audit_event(self, user_id: str, action: str, 
                       resource_type: str, resource_id: str,
                       ip_address: str = None, details: Optional[Dict[str, Any]] = None):
        """Log audit events to database and file"""
        # Log to file
        log_entry = {
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'ip_address': ip_address,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['audit'].info(json.dumps(log_entry))
        
        # Also save to database
        db = SessionLocal()
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                details=json.dumps(details) if details else None
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            self.loggers['error'].error(f"Failed to save audit log to database: {e}")
        finally:
            db.close()
    
    def log_security_event(self, event_type: str, severity: str,
                          message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log security-related events"""
        log_entry = {
            'event_type': event_type,
            'severity': severity,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger = self.loggers['security']
        
        if severity == 'CRITICAL':
            logger.critical(json.dumps(log_entry))
        elif severity == 'HIGH':
            logger.error(json.dumps(log_entry))
        elif severity == 'MEDIUM':
            logger.warning(json.dumps(log_entry))
        else:
            logger.info(json.dumps(log_entry))
    
    def log_error(self, component: str, error_type: str, 
                 message: str, traceback: str = None):
        """Log errors"""
        log_entry = {
            'component': component,
            'error_type': error_type,
            'message': message,
            'traceback': traceback,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['error'].error(json.dumps(log_entry))
    
    def log_task_execution(self, task_id: str, agent_id: str, 
                          command: str, status: str, 
                          execution_time: float = None,
                          error: str = None):
        """Log task execution details"""
        log_entry = {
            'task_id': task_id,
            'agent_id': agent_id,
            'command': command,
            'status': status,
            'execution_time': execution_time,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['agent'].info(json.dumps(log_entry))
    
    def log_authentication(self, username: str, success: bool, 
                         ip_address: str, reason: str = None):
        """Log authentication attempts"""
        event_type = 'auth_success' if success else 'auth_failure'
        severity = 'INFO' if success else 'MEDIUM'
        
        self.log_security_event(
            event_type=event_type,
            severity=severity,
            message=f"Authentication {'succeeded' if success else 'failed'} for {username}",
            metadata={
                'username': username,
                'ip_address': ip_address,
                'reason': reason
            }
        )
    
    def log_listener_event(self, listener_id: str, event_type: str,
                          message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log listener events"""
        log_entry = {
            'listener_id': listener_id,
            'event_type': event_type,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.loggers['server'].info(json.dumps(log_entry))
    
    async def search_logs(self, log_type: str, filters: Dict[str, Any],
                         start_time: datetime = None, 
                         end_time: datetime = None,
                         limit: int = 1000) -> List[Dict[str, Any]]:
        """Search logs with filters"""
        results = []
        
        # Determine which log file to search
        log_files = []
        if log_type == 'all':
            log_files = [f for f in self.log_dir.glob('*.log')]
        else:
            log_file = self.log_dir / f'c2_{log_type}.log'
            if log_file.exists():
                log_files = [log_file]
        
        # Search each log file
        for log_file in log_files:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        # Parse log entry
                        if ' - ' in line:
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                timestamp_str = parts[0]
                                log_data = json.loads(parts[3])
                                
                                # Check time range
                                if start_time or end_time:
                                    log_time = datetime.fromisoformat(
                                        log_data.get('timestamp', timestamp_str)
                                    )
                                    if start_time and log_time < start_time:
                                        continue
                                    if end_time and log_time > end_time:
                                        continue
                                
                                # Check filters
                                match = True
                                for key, value in filters.items():
                                    if key not in log_data or log_data[key] != value:
                                        match = False
                                        break
                                
                                if match:
                                    results.append(log_data)
                                    if len(results) >= limit:
                                        return results
                                        
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        return results
    
    async def get_statistics(self, time_range: timedelta = None) -> Dict[str, Any]:
        """Get log statistics"""
        stats = {
            'total_events': 0,
            'events_by_type': {},
            'errors': 0,
            'security_events': 0,
            'authentication_attempts': 0,
            'task_executions': 0
        }
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - time_range if time_range else None
        
        # Count events in each log
        for log_type in ['server', 'agent', 'audit', 'security', 'error']:
            events = await self.search_logs(
                log_type, {}, start_time, end_time, limit=10000
            )
            
            stats['total_events'] += len(events)
            
            if log_type == 'error':
                stats['errors'] = len(events)
            elif log_type == 'security':
                stats['security_events'] = len(events)
                stats['authentication_attempts'] = len([
                    e for e in events 
                    if e.get('event_type') in ['auth_success', 'auth_failure']
                ])
            elif log_type == 'agent':
                stats['task_executions'] = len([
                    e for e in events 
                    if e.get('event_type') == 'task_execution'
                ])
            
            # Count by event type
            for event in events:
                event_type = event.get('event_type', 'unknown')
                stats['events_by_type'][event_type] = \
                    stats['events_by_type'].get(event_type, 0) + 1
        
        return stats
    
    async def _log_maintenance_task(self):
        """Background task for log maintenance"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Compress old log files
                if self.compression_enabled:
                    await self._compress_old_logs()
                
                # Clean up old compressed logs
                await self._cleanup_old_logs()
                
                # Update statistics
                await self._update_log_statistics()
                
            except Exception as e:
                self.log_error(
                    'log_manager',
                    'maintenance_error',
                    str(e)
                )
    
    async def _compress_old_logs(self):
        """Compress rotated log files"""
        for log_file in self.log_dir.glob('*.log.*'):
            if not log_file.suffix.endswith('.gz'):
                # Compress file
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove original
                os.remove(log_file)
                
                self.log_server_event(
                    'log_compressed',
                    f'Compressed log file: {log_file.name}'
                )
    
    async def _cleanup_old_logs(self):
        """Remove old compressed logs"""
        # Keep logs for 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        for log_file in self.log_dir.glob('*.gz'):
            # Check file modification time
            file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            if file_time < cutoff_date:
                os.remove(log_file)
                
                self.log_server_event(
                    'log_deleted',
                    f'Deleted old log file: {log_file.name}'
                )
    
    async def _update_log_statistics(self):
        """Update log statistics cache"""
        # Calculate statistics for different time ranges
        for time_range in [timedelta(hours=1), timedelta(days=1), timedelta(days=7)]:
            stats = await self.get_statistics(time_range)
            
            # Cache statistics (could save to Redis)
            cache_key = f'log_stats_{int(time_range.total_seconds())}'
            # TODO: Save to cache
    
    def export_logs(self, log_type: str, start_time: datetime,
                   end_time: datetime, format: str = 'json') -> str:
        """Export logs to file"""
        # Search logs
        logs = asyncio.run(self.search_logs(
            log_type, {}, start_time, end_time, limit=100000
        ))
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        export_dir = self.log_dir / 'exports'
        export_dir.mkdir(exist_ok=True)
        
        if format == 'json':
            export_file = export_dir / f'{log_type}_export_{timestamp}.json'
            with open(export_file, 'w') as f:
                json.dump(logs, f, indent=2)
        
        elif format == 'csv':
            import csv
            export_file = export_dir / f'{log_type}_export_{timestamp}.csv'
            
            if logs:
                # Get all unique keys
                all_keys = set()
                for log in logs:
                    all_keys.update(log.keys())
                
                with open(export_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                    writer.writeheader()
                    writer.writerows(logs)
        
        return str(export_file)

# Global log manager instance
log_manager = LogManager()
