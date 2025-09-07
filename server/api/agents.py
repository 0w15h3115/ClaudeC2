"""
Agent management API endpoints
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from core.database import get_db, redis_client
from core.models import Agent, Task, OperatorSession
from core.schemas import AgentCheckIn, AgentResponse, AgentUpdate
from api.auth import get_current_user, User
import json

router = APIRouter()

@router.post("/checkin")
async def agent_checkin(
    checkin_data: AgentCheckIn,
    db: Session = Depends(get_db)
):
    """Handle agent check-in"""
    # Verify session exists
    session = db.query(OperatorSession).filter(
        OperatorSession.id == checkin_data.session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if checkin_data.agent_id:
        # Existing agent checking in
        agent = db.query(Agent).filter(Agent.id == checkin_data.agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        # Update agent info
        agent.last_seen = datetime.utcnow()
        agent.status = "active"
        agent.external_ip = checkin_data.external_ip
        agent.hostname = checkin_data.hostname
        agent.username = checkin_data.username
        
    else:
        # New agent registration
        agent = Agent(
            session_id=checkin_data.session_id,
            hostname=checkin_data.hostname,
            username=checkin_data.username,
            platform=checkin_data.platform,
            architecture=checkin_data.architecture,
            process_id=checkin_data.process_id,
            internal_ip=checkin_data.internal_ip,
            external_ip=checkin_data.external_ip,
            status="active"
        )
        db.add(agent)
    
    db.commit()
    db.refresh(agent)
    
    # Get pending tasks
    pending_tasks = db.query(Task).filter(
        and_(Task.agent_id == agent.id, Task.status == "pending")
    ).all()
    
    # Mark tasks as sent
    task_list = []
    for task in pending_tasks:
        task.status = "sent"
        task.sent_at = datetime.utcnow()
        task_list.append({
            "id": task.id,
            "command": task.command,
            "parameters": json.loads(task.parameters) if task.parameters else {}
        })
    
    db.commit()
    
    # Notify via Redis pub/sub
    if redis_client:
        await redis_client.publish(
            f"agent:{agent.id}",
            json.dumps({"event": "checkin", "agent_id": agent.id})
        )
    
    return {
        "agent_id": agent.id,
        "tasks": task_list,
        "sleep_interval": agent.sleep_interval,
        "jitter": agent.jitter
    }

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agents"""
    query = db.query(Agent)
    
    # Filter by session if provided
    if session_id:
        query = query.filter(Agent.session_id == session_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Agent.status == status)
    
    # Non-admin users can only see their own agents
    if current_user.role != "admin":
        user_sessions = db.query(OperatorSession.id).filter(
            OperatorSession.user_id == current_user.id
        ).subquery()
        query = query.filter(Agent.session_id.in_(user_sessions))
    
    agents = query.all()
    return agents

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific agent details"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Check permissions
    if current_user.role != "admin":
        session = db.query(OperatorSession).filter(
            and_(
                OperatorSession.id == agent.session_id,
                OperatorSession.user_id == current_user.id
            )
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return agent

@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    update_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update agent settings"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Update fields
    if update_data.sleep_interval is not None:
        agent.sleep_interval = update_data.sleep_interval
    if update_data.jitter is not None:
        agent.jitter = update_data.jitter
    if update_data.status is not None:
        agent.status = update_data.status
    
    db.commit()
    db.refresh(agent)
    
    return agent

@router.delete("/{agent_id}")
async def remove_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove an agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Mark as dead instead of deleting
    agent.status = "dead"
    db.commit()
    
    return {"status": "success", "message": "Agent marked as dead"}

@router.post("/{agent_id}/tasks")
async def create_task(
    agent_id: str,
    task_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task for an agent"""
    # Import here to avoid circular dependency
    from api.tasks import create_agent_task
    
    return await create_agent_task(
        agent_id=agent_id,
        task_data=task_data,
        current_user=current_user,
        db=db
    )
