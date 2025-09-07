"""
Session management API endpoints
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import OperatorSession, Agent
from core.schemas import SessionCreate, SessionResponse, SessionUpdate
from api.auth import get_current_user, User

router = APIRouter()

@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new operation session"""
    # Check if session name already exists for this user
    existing = db.query(OperatorSession).filter(
        OperatorSession.user_id == current_user.id,
        OperatorSession.name == session_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session with this name already exists"
        )
    
    # Create new session
    session = OperatorSession(
        user_id=current_user.id,
        name=session_data.name,
        description=session_data.description
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all sessions for current user"""
    query = db.query(OperatorSession)
    
    # Admin can see all sessions
    if current_user.role != "admin":
        query = query.filter(OperatorSession.user_id == current_user.id)
    
    # Filter inactive if requested
    if not include_inactive:
        query = query.filter(OperatorSession.is_active == True)
    
    sessions = query.order_by(OperatorSession.created_at.desc()).all()
    
    # Add agent count to each session
    for session in sessions:
        session.agent_count = db.query(Agent).filter(
            Agent.session_id == session.id
        ).count()
    
    return sessions

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific session details"""
    session = db.query(OperatorSession).filter(
        OperatorSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Add agent count
    session.agent_count = db.query(Agent).filter(
        Agent.session_id == session.id
    ).count()
    
    return session

@router.put("/{session_id}")
async def update_session(
    session_id: str,
    update_data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update session details"""
    session = db.query(OperatorSession).filter(
        OperatorSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    if update_data.name is not None:
        session.name = update_data.name
    if update_data.description is not None:
        session.description = update_data.description
    if update_data.is_active is not None:
        session.is_active = update_data.is_active
    
    db.commit()
    db.refresh(session)
    
    return session

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a session (soft delete)"""
    session = db.query(OperatorSession).filter(
        OperatorSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check permissions
    if current_user.role != "admin" and session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if there are active agents
    active_agents = db.query(Agent).filter(
        Agent.session_id == session_id,
        Agent.status == "active"
    ).count()
    
    if active_agents > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete session with {active_agents} active agents"
        )
    
    # Soft delete
    session.is_active = False
    db.commit()
    
    return {"status": "success", "message": "Session deactivated"}

@router.post("/{session_id}/clone")
async def clone_session(
    session_id: str,
    new_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clone an existing session"""
    original = db.query(OperatorSession).filter(
        OperatorSession.id == session_id
    ).first()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Create clone
    clone = OperatorSession(
        user_id=current_user.id,
        name=new_name,
        description=f"Clone of {original.name}. {original.description or ''}"
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    
    return clone
