"""
Task management API endpoints
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from core.database import get_db, redis_client
from core.models import Task, Agent, OperatorSession
from core.schemas import TaskCreate, TaskResponse, TaskResult
from api.auth import get_current_user, User
import json

router = APIRouter()

async def create_agent_task(
    agent_id: str,
    task_data: TaskCreate,
    current_user: User,
    db: Session
):
    """Create a task for an agent (internal function)"""
    # Verify agent exists
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
    
    # Create task
    task = Task(
        agent_id=agent_id,
        command=task_data.command,
        parameters=json.dumps(task_data.parameters) if task_data.parameters else None,
        created_by=current_user.id,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Notify via Redis
    if redis_client:
        await redis_client.publish(
            f"agent:{agent_id}",
            json.dumps({"event": "new_task", "task_id": task.id})
        )
    
    return task

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List tasks with optional filters"""
    query = db.query(Task)
    
    # Filter by agent if provided
    if agent_id:
        query = query.filter(Task.agent_id == agent_id)
    
    # Filter by status if provided
    if status:
        query = query.filter(Task.status == status)
    
    # Non-admin users can only see tasks for their agents
    if current_user.role != "admin":
        user_sessions = db.query(OperatorSession.id).filter(
            OperatorSession.user_id == current_user.id
        ).subquery()
        user_agents = db.query(Agent.id).filter(
            Agent.session_id.in_(user_sessions)
        ).subquery()
        query = query.filter(Task.agent_id.in_(user_agents))
    
    # Apply pagination and ordering
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific task details"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions
    if current_user.role != "admin":
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
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
    
    return task

@router.post("/{task_id}/result")
async def submit_task_result(
    task_id: str,
    result_data: TaskResult,
    db: Session = Depends(get_db)
):
    """Submit task result from agent"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update task with result
    task.status = result_data.status
    task.result = result_data.result
    task.error = result_data.error
    task.completed_at = datetime.utcnow()
    
    db.commit()
    
    # Notify via Redis
    if redis_client:
        await redis_client.publish(
            f"task:{task_id}",
            json.dumps({
                "event": "task_complete",
                "task_id": task_id,
                "status": result_data.status
            })
        )
    
    return {"status": "success"}

@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Only pending tasks can be cancelled
    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending tasks can be cancelled"
        )
    
    task.status = "cancelled"
    task.completed_at = datetime.utcnow()
    db.commit()
    
    return {"status": "success", "message": "Task cancelled"}

@router.post("/bulk")
async def create_bulk_tasks(
    task_data: TaskCreate,
    agent_ids: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create the same task for multiple agents"""
    created_tasks = []
    
    for agent_id in agent_ids:
        try:
            task = await create_agent_task(
                agent_id=agent_id,
                task_data=task_data,
                current_user=current_user,
                db=db
            )
            created_tasks.append(task)
        except HTTPException:
            # Skip agents that user doesn't have access to
            continue
    
    return {
        "status": "success",
        "tasks_created": len(created_tasks),
        "tasks": created_tasks
    }
