"""API endpoints for Whitelist Hub."""

import os
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .connection_manager import ProjectAnalysisManager
from .project_analysis_service import ProjectAnalysisService
from ..models.message import MessageType, MessageStructure
from ..db.mongodb import connect_to_mongo, close_mongo_connection
from ..core.config import settings

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Whitelist Hub API",
    description="API for blockchain project analysis with focus on whitelist mechanisms",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize connection manager
connection_manager = ProjectAnalysisManager()

# Define API models
class ProjectStartRequest(BaseModel):
    """Request model for starting a project analysis."""
    
    project_name: str = Field(..., description="Project name to analyze")
    website: Optional[str] = Field(None, description="Project website URL")
    github_url: Optional[str] = Field(None, description="Project GitHub URL")

class MessageRequest(BaseModel):
    """Request model for sending a message."""
    
    text: str = Field(..., description="Message text")

class ContractAnalysisRequest(BaseModel):
    """Request model for analyzing a contract."""
    
    contract_address: str = Field(..., description="Contract address to analyze")
    blockchain: str = Field("ethereum", description="Blockchain name (e.g., ethereum, bsc)")

class SessionResponse(BaseModel):
    """Response model for session creation."""
    
    session_id: str = Field(..., description="Session ID")
    created_at: str = Field(..., description="Session creation timestamp")

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Dependency for getting project analysis service
async def get_project_analysis_service() -> ProjectAnalysisService:
    """Dependency for getting project analysis service."""
    return await ProjectAnalysisService.create()

# API Routes
@app.get("/", tags=["general"])
async def root():
    """Root endpoint for health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/sessions", response_model=SessionResponse, tags=["session"])
async def create_session():
    """Create a new analysis session."""
    session_id = str(uuid.uuid4())
    connection_manager.session_data[session_id] = {
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
        "project_data": None,
        "analysis_status": "not_started"
    }
    
    return {
        "session_id": session_id,
        "created_at": connection_manager.session_data[session_id]["created_at"]
    }

@app.get("/api/sessions/{session_id}", tags=["session"])
async def get_session(session_id: str):
    """Get session data."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return connection_manager.session_data[session_id]

@app.post("/api/sessions/{session_id}/projects", tags=["project"])
async def start_project_analysis(
    session_id: str,
    project_request: ProjectStartRequest,
    background_tasks: BackgroundTasks,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Start a new project analysis."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session data
    connection_manager.update_session_data(session_id, {
        "project_name": project_request.project_name,
        "website": project_request.website,
        "github_url": project_request.github_url,
        "analysis_status": "in_progress"
    })
    
    # Define message callback
    async def message_callback(message):
        await connection_manager.send_message(session_id, message)
    
    # Start analysis in background
    background_tasks.add_task(
        service.analyze_project,
        project_name=project_request.project_name,
        website=project_request.website,
        github_url=project_request.github_url,
        session_id=session_id,
        message_callback=message_callback
    )
    
    return {
        "status": "started",
        "session_id": session_id,
        "project_name": project_request.project_name,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/sessions/{session_id}/contracts", tags=["contract"])
async def analyze_contract(
    session_id: str,
    contract_request: ContractAnalysisRequest,
    background_tasks: BackgroundTasks,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Analyze a specific contract."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Define message callback
    async def message_callback(message):
        await connection_manager.send_message(session_id, message)
    
    # Start analysis in background
    background_tasks.add_task(
        service.analyze_contract,
        contract_address=contract_request.contract_address,
        blockchain=contract_request.blockchain,
        session_id=session_id,
        message_callback=message_callback
    )
    
    return {
        "status": "started",
        "session_id": session_id,
        "contract_address": contract_request.contract_address,
        "blockchain": contract_request.blockchain,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/sessions/{session_id}/messages", tags=["message"])
async def send_message(
    session_id: str,
    message_request: MessageRequest,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Send a message in a session."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add user message to session
    user_message = MessageStructure.format_message("user", message_request.text)
    await connection_manager.save_message(session_id, "user", message_request.text)
    
    # Process message using AI
    thinking_message = MessageStructure.format_thinking()
    await connection_manager.send_message(session_id, thinking_message)
    
    # Get response from AI
    response_text = await service.process_message(
        session_id=session_id,
        message=message_request.text
    )
    
    # Send AI response
    assistant_message = MessageStructure.format_ai_response(response_text)
    await connection_manager.save_message(session_id, "assistant", response_text)
    await connection_manager.send_message(session_id, assistant_message)
    
    return assistant_message

@app.get("/api/sessions/{session_id}/messages", tags=["message"])
async def get_messages(session_id: str):
    """Get all messages in a session."""
    if session_id not in connection_manager.session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "messages": connection_manager.get_messages(session_id)
    }

@app.get("/api/projects/{project_name}", tags=["project"])
async def get_project_data(
    project_name: str,
    service: ProjectAnalysisService = Depends(get_project_analysis_service)
):
    """Get project data by name."""
    project_data = await service.get_project_data(project_name)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project_data

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    # Connect client
    success = await connection_manager.connect(session_id, websocket)
    if not success:
        return
    
    # Send welcome message
    welcome_message = MessageStructure.format_system(
        "Welcome to Whitelist Hub! You can start by analyzing a project or a specific contract."
    )
    await connection_manager.send_message(session_id, welcome_message)
    
    try:
        # Handle WebSocket messages
        while True:
            data = await websocket.receive_text()
            await connection_manager.handle_client_message(session_id, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
    except Exception as e:
        logger.exception(f"Error in WebSocket handler: {e}")
        try:
            await connection_manager.send_message(
                session_id,
                MessageStructure.format_error(f"Error: {str(e)}")
            )
        except:
            pass
        connection_manager.disconnect(session_id)
