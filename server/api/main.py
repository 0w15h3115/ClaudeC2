#!/usr/bin/env python3
"""
C2 Team Server - Main API Entry Point
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from core.database import engine, Base
from core.config import settings
from api.auth import router as auth_router
from api.agents import router as agents_router
from api.tasks import router as tasks_router
from api.sessions import router as sessions_router
from api.listeners import router as listeners_router

# Global Redis client
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    global redis_client
    redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize default admin user
    from core.security import create_default_admin
    create_default_admin()
    
    yield
    
    # Shutdown
    await redis_client.close()

# Create FastAPI app
app = FastAPI(
    title="C2 Team Server API",
    description="Command and Control Framework for Authorized Security Testing",
    version="2.0.0",
    lifespan=lifespan
)

# Startup event handler
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("Running startup event handler...")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Admin username: {settings.DEFAULT_ADMIN_USERNAME}")
    print(f"Admin password: {settings.DEFAULT_ADMIN_PASSWORD}")
    from core.security import create_default_admin
    create_default_admin()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(listeners_router, prefix="/api/listeners", tags=["Listeners"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "C2 Team Server",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if redis_client else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVER_PORT)
