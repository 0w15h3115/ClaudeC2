"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

from core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Redis client (initialized in main.py)
redis_client = None

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_redis():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    return redis_client

def init_db():
    """Initialize database tables"""
    # Import all models to register them
    from core import models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
