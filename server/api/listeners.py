"""
Listener management API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Listener
from core.schemas import ListenerCreate, ListenerResponse, ListenerUpdate
from api.auth import get_current_user, require_role, User
from listeners.manager import ListenerManager
import json

router = APIRouter()
listener_manager = ListenerManager()

@router.post("/", response_model=ListenerResponse)
async def create_listener(
    listener_data: ListenerCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db)
):
    """Create and start a new listener"""
    # Check if name already exists
    existing = db.query(Listener).filter(
        Listener.name == listener_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listener with this name already exists"
        )
    
    # Check if port is already in use
    port_in_use = db.query(Listener).filter(
        Listener.bind_port == listener_data.bind_port,
        Listener.is_active == True
    ).first()
    
    if port_in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port {listener_data.bind_port} is already in use"
        )
    
    # Create listener record
    listener = Listener(
        name=listener_data.name,
        type=listener_data.type,
        bind_address=listener_data.bind_address,
        bind_port=listener_data.bind_port,
        configuration=json.dumps(listener_data.configuration)
    )
    db.add(listener)
    db.commit()
    db.refresh(listener)
    
    # Start listener in background
    background_tasks.add_task(
        listener_manager.start_listener,
        listener.id,
        listener_data
    )
    
    return listener

@router.get("/", response_model=List[ListenerResponse])
async def list_listeners(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all listeners"""
    query = db.query(Listener)
    
    if not include_inactive:
        query = query.filter(Listener.is_active == True)
    
    listeners = query.all()
    
    # Add runtime status
    for listener in listeners:
        listener.is_running = listener_manager.is_running(listener.id)
    
    return listeners

@router.get("/{listener_id}", response_model=ListenerResponse)
async def get_listener(
    listener_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific listener details"""
    listener = db.query(Listener).filter(
        Listener.id == listener_id
    ).first()
    
    if not listener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listener not found"
        )
    
    # Add runtime status
    listener.is_running = listener_manager.is_running(listener.id)
    
    return listener

@router.put("/{listener_id}")
async def update_listener(
    listener_id: str,
    update_data: ListenerUpdate,
    current_user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db)
):
    """Update listener configuration"""
    listener = db.query(Listener).filter(
        Listener.id == listener_id
    ).first()
    
    if not listener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listener not found"
        )
    
    # Can't update while running
    if listener_manager.is_running(listener_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update running listener. Stop it first."
        )
    
    # Update fields
    if update_data.bind_address is not None:
        listener.bind_address = update_data.bind_address
    if update_data.bind_port is not None:
        listener.bind_port = update_data.bind_port
    if update_data.configuration is not None:
        listener.configuration = json.dumps(update_data.configuration)
    
    db.commit()
    db.refresh(listener)
    
    return listener

@router.post("/{listener_id}/start")
async def start_listener(
    listener_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db)
):
    """Start a stopped listener"""
    listener = db.query(Listener).filter(
        Listener.id == listener_id
    ).first()
    
    if not listener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listener not found"
        )
    
    if listener_manager.is_running(listener_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listener is already running"
        )
    
    # Start listener
    background_tasks.add_task(
        listener_manager.start_listener,
        listener_id,
        listener
    )
    
    return {"status": "success", "message": "Listener starting"}

@router.post("/{listener_id}/stop")
async def stop_listener(
    listener_id: str,
    current_user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db)
):
    """Stop a running listener"""
    listener = db.query(Listener).filter(
        Listener.id == listener_id
    ).first()
    
    if not listener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listener not found"
        )
    
    if not listener_manager.is_running(listener_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listener is not running"
        )
    
    # Stop listener
    listener_manager.stop_listener(listener_id)
    
    return {"status": "success", "message": "Listener stopped"}

@router.delete("/{listener_id}")
async def delete_listener(
    listener_id: str,
    current_user: User = Depends(require_role("operator")),
    db: Session = Depends(get_db)
):
    """Delete a listener"""
    listener = db.query(Listener).filter(
        Listener.id == listener_id
    ).first()
    
    if not listener:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listener not found"
        )
    
    # Stop if running
    if listener_manager.is_running(listener_id):
        listener_manager.stop_listener(listener_id)
    
    # Soft delete
    listener.is_active = False
    db.commit()
    
    return {"status": "success", "message": "Listener deleted"}
