"""
Report generation service for creating operational reports
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import base64
from io import BytesIO

from core.database import SessionLocal
from core.models import (
    OperatorSession, Agent, Task, Download, 
    Credential, AuditLog, User
)
from core.config import settings

class ReportGenerator:
    """Generate various reports for C2 operations"""
    
    def __init__(self):
        self.output_dir = Path(settings.DOWNLOAD_DIR) / "reports"
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_executive_summary(
        self, 
        session_id: str,
        include_credentials: bool = True,
        include_downloads: bool = True,
        classification: str = "TLP:RED"
    ) -> str:
        """Generate executive summary report"""
        
        db = SessionLocal()
        try:
            # Get session
            session = db.query(OperatorSession).filter(
                OperatorSession.id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # Gather statistics
            agents = db.query(Agent).filter(Agent.session_id == session_id).all()
            tasks = db.query(Task).join(Agent).filter(Agent.session_id == session_id).all()
            
            total_agents = len(agents)
            active_agents = len([a for a in agents if a.status == 'active'])
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == 'completed'])
            success_rate = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            
            # Build report data
            report = {
                "metadata": {
                    "report_id": f"RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    "session_name": session.name,
                    "session_id": session_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "classification": classification
                },
                "summary": {
                    "total_agents": total_agents,
                    "active_agents": active_agents,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "success_rate": success_rate
                },
                "agents": [],
                "task_statistics": {},
                "timeline": []
            }
            
            # Add agent details
            for agent in agents:
                report["agents"].append({
                    "hostname": agent.hostname,
                    "username": agent.username,
                    "platform": agent.platform,
                    "internal_ip": agent.internal_ip,
                    "status": agent.status,
                    "first_seen": agent.first_seen.isoformat(),
                    "last_seen": agent.last_seen.isoformat()
                })
            
            # Task statistics by command
            task_stats = {}
            for task in tasks:
                if task.command not in task_stats:
                    task_stats[task.command] = {
                        "total": 0,
                        "completed": 0,
                        "failed": 0
                    }
                task_stats[task.command]["total"] += 1
                if task.status == "completed":
                    task_stats[task.command]["completed"] += 1
                elif task.status == "failed":
                    task_stats[task.command]["failed"] += 1
            
            report["task_statistics"] = task_stats
            
            # Add credentials if requested
            if include_credentials:
                credentials = db.query(Credential).join(Agent).filter(
                    Agent.session_id == session_id
                ).all()
                
                report["credentials"] = [{
                    "type": cred.type,
                    "username": cred.username,
                    "domain": cred.domain,
                    "host": cred.host,
                    "service": cred.service,
                    "harvested_at": cred.harvested_at.isoformat()
                } for cred in credentials]
            
            # Add downloads if requested
            if include_downloads:
                downloads = db.query(Download).join(Agent).filter(
                    Agent.session_id == session_id
                ).all()
                
                report["downloads"] = [{
                    "filename": dl.filename,
                    "file_path": dl.file_path,
                    "file_size": dl.file_size,
                    "file_hash": dl.file_hash,
                    "downloaded_at": dl.downloaded_at.isoformat()
                } for dl in downloads]
            
            # Generate timeline
            timeline_events = []
            
            # Session creation
            timeline_events.append({
                "timestamp": session.created_at.isoformat(),
                "event": "session_created",
                "description": f"Operation '{session.name}' started"
            })
            
            # Agent connections
            for agent in agents:
                timeline_events.append({
                    "timestamp": agent.first_seen.isoformat(),
                    "event": "agent_connected",
                    "description": f"Agent connected: {agent.hostname} ({agent.internal_ip})"
                })
            
            # Sort timeline
            timeline_events.sort(key=lambda x: x["timestamp"])
            report["timeline"] = timeline_events
            
            # Save report
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            report_path = self.output_dir / f"exec_summary_{session_id}_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            return str(report_path)
            
        finally:
            db.close()
    
    async def generate_ioc_report(self, session_id: str) -> str:
        """Generate Indicators of Compromise report"""
        
        db = SessionLocal()
        try:
            iocs = {
                "metadata": {
                    "session_id": session_id,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "indicators": {
                    "file_hashes": [],
                    "ip_addresses": [],
                    "domains": [],
                    "filenames": [],
                    "processes": [],
                    "registry_keys": []
                }
            }
            
            # Get agents
            agents = db.query(Agent).filter(Agent.session_id == session_id).all()
            
            # Collect IP addresses
            for agent in agents:
                if agent.external_ip:
                    iocs["indicators"]["ip_addresses"].append({
                        "value": agent.external_ip,
                        "type": "c2_callback",
                        "context": f"External IP for {agent.hostname}"
                    })
            
            # Collect file hashes from downloads
            downloads = db.query(Download).join(Agent).filter(
                Agent.session_id == session_id
            ).all()
            
            for dl in downloads:
                if dl.file_hash:
                    iocs["indicators"]["file_hashes"].append({
                        "value": dl.file_hash,
                        "algorithm": "SHA256",
                        "filename": dl.filename,
                        "file_path": dl.file_path
                    })
                
                iocs["indicators"]["filenames"].append({
                    "value": dl.filename,
                    "path": dl.file_path
                })
            
            # Save IOC report
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            ioc_path = self.output_dir / f"ioc_{session_id}_{timestamp}.json"
            
            with open(ioc_path, 'w') as f:
                json.dump(iocs, f, indent=2)
            
            # Also generate CSV version
            csv_path = await self._generate_ioc_csv(session_id, iocs)
            
            return str(ioc_path)
            
        finally:
            db.close()
    
    async def _generate_ioc_csv(self, session_id: str, iocs: Dict[str, Any]) -> str:
        """Generate CSV file with IOCs"""
        import csv
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        csv_path = self.output_dir / f"ioc_{session_id}_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Value', 'Context'])
            
            # File hashes
            for ioc in iocs["indicators"]["file_hashes"]:
                writer.writerow([
                    f"File Hash ({ioc['algorithm']})",
                    ioc['value'],
                    f"{ioc['filename']} - {ioc['file_path']}"
                ])
            
            # IP addresses
            for ioc in iocs["indicators"]["ip_addresses"]:
                writer.writerow([
                    "IP Address",
                    ioc['value'],
                    ioc['context']
                ])
            
            # Filenames
            for ioc in iocs["indicators"]["filenames"]:
                writer.writerow([
                    "Filename",
                    ioc['value'],
                    ioc['path']
                ])
        
        return str(csv_path)
    
    async def generate_timeline_report(self, session_id: str) -> str:
        """Generate detailed timeline report"""
        
        db = SessionLocal()
        try:
            events = []
            
            # Get session
            session = db.query(OperatorSession).filter(
                OperatorSession.id == session_id
            ).first()
            
            # Session events
            events.append({
                "timestamp": session.created_at.isoformat(),
                "type": "session",
                "description": f"Session '{session.name}' created",
                "operator": session.user.username if session.user else "Unknown"
            })
            
            # Agent events
            agents = db.query(Agent).filter(Agent.session_id == session_id).all()
            for agent in agents:
                events.append({
                    "timestamp": agent.first_seen.isoformat(),
                    "type": "agent_connect",
                    "description": f"Agent connected: {agent.hostname} ({agent.internal_ip})",
                    "agent_id": agent.id
                })
            
            # Task events
            tasks = db.query(Task).join(Agent).filter(
                Agent.session_id == session_id
            ).all()
            
            for task in tasks:
                events.append({
                    "timestamp": task.created_at.isoformat(),
                    "type": "task_created",
                    "description": f"Task created: {task.command}",
                    "operator": task.creator.username if task.creator else "Unknown"
                })
                
                if task.completed_at:
                    events.append({
                        "timestamp": task.completed_at.isoformat(),
                        "type": "task_completed",
                        "description": f"Task {task.command} {task.status}",
                        "task_id": task.id
                    })
            
            # Download events
            downloads = db.query(Download).join(Agent).filter(
                Agent.session_id == session_id
            ).all()
            
            for dl in downloads:
                events.append({
                    "timestamp": dl.downloaded_at.isoformat(),
                    "type": "file_download",
                    "description": f"Downloaded: {dl.filename} ({dl.file_size} bytes)",
                    "agent_id": dl.agent_id
                })
            
            # Sort events
            events.sort(key=lambda x: x["timestamp"])
            
            # Create timeline report
            timeline_report = {
                "metadata": {
                    "session_id": session_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "total_events": len(events)
                },
                "events": events
            }
            
            # Save report
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            timeline_path = self.output_dir / f"timeline_{session_id}_{timestamp}.json"
            
            with open(timeline_path, 'w') as f:
                json.dump(timeline_report, f, indent=2)
            
            return str(timeline_path)
            
        finally:
            db.close()
    
    async def generate_mitre_attack_report(self, session_id: str) -> str:
        """Generate MITRE ATT&CK mapping report"""
        
        # Command to MITRE technique mapping
        mitre_mapping = {
            'shell': ['T1059.003', 'T1059.001'],  # Command and Scripting Interpreter
            'ps': ['T1057'],  # Process Discovery
            'pslist': ['T1057'],
            'download': ['T1005'],  # Data from Local System
            'upload': ['T1105'],  # Ingress Tool Transfer
            'persist': ['T1547', 'T1546'],  # Persistence
            'keylog': ['T1056.001'],  # Input Capture: Keylogging
            'screenshot': ['T1113'],  # Screen Capture
            'hashdump': ['T1003'],  # OS Credential Dumping
            'netstat': ['T1049'],  # System Network Connections Discovery
            'portscan': ['T1046'],  # Network Service Scanning
            'filebrowser': ['T1083'],  # File and Directory Discovery
            'whoami': ['T1033'],  # System Owner/User Discovery
            'sysinfo': ['T1082'],  # System Information Discovery
        }
        
        db = SessionLocal()
        try:
            # Get all tasks
            tasks = db.query(Task).join(Agent).filter(
                Agent.session_id == session_id
            ).all()
            
            # Count techniques
            techniques_used = {}
            for task in tasks:
                if task.command in mitre_mapping:
                    for technique in mitre_mapping[task.command]:
                        if technique not in techniques_used:
                            techniques_used[technique] = {
                                'count': 0,
                                'commands': []
                            }
                        techniques_used[technique]['count'] += 1
                        if task.command not in techniques_used[technique]['commands']:
                            techniques_used[technique]['commands'].append(task.command)
            
            # Create report
            mitre_report = {
                "metadata": {
                    "session_id": session_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "framework_version": "MITRE ATT&CK v13"
                },
                "statistics": {
                    "total_techniques": len(techniques_used),
                    "total_tasks": len(tasks)
                },
                "techniques": techniques_used
            }
            
            # Save report
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            mitre_path = self.output_dir / f"mitre_attack_{session_id}_{timestamp}.json"
            
            with open(mitre_path, 'w') as f:
                json.dump(mitre_report, f, indent=2)
            
            return str(mitre_path)
            
        finally:
            db.close()

# Global report generator instance
report_generator = ReportGenerator()
