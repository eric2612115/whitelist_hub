"""
FastAPI implementation for Whitelist Hub.

This module provides the FastAPI application with REST and WebSocket endpoints
for interacting with the Whitelist Hub system.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .connection_manager import get_connection_manager, WebSocketMessage
from .session_manager import get_session_manager, Session
from ..agent_framework.context import Context
from ..agent_framework.workflow import WorkflowConfig, Workflow
from ..utils.observability import LoggingEventListener
from ..services.ai_client import AIModelProvider

logger = logging.getLogger(__name__)


# Input and output models
class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session information."""
    id: str
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None
    project_name: Optional[str] = None
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageRequest(BaseModel):
    """Request model for sending a message."""
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Response model for a message."""
    id: str
    text: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectAnalysisRequest(BaseModel):
    """Request model for starting a project analysis."""
    project_name: str
    website: Optional[str] = None
    github_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    id: str
    status: str
    progress: float
    tasks_total: int
    tasks_completed: int
    tasks_failed: int
    started_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def create_app() -> FastAPI:
    """Create the FastAPI application.
    
    Returns:
        The FastAPI application
    """
    app = FastAPI(
        title="Whitelist Hub API",
        description="API for Whitelist Hub blockchain project analysis",
        version="0.1.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Set up event listeners
    logging_listener = LoggingEventListener()
    session_manager = get_session_manager()
    session_manager.add_global_listener(logging_listener)
    
    connection_manager = get_connection_manager()
    connection_manager.add_global_listener(logging_listener)
    
    
    # Session endpoints
    @app.post("/api/sessions", response_model=SessionResponse)
    async def create_session(request: CreateSessionRequest):
        """Create a new session."""
        session = await session_manager.create_session(request.user_id)
        return SessionResponse(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            user_id=session.user_id,
            project_name=session.project_name,
            status=session.status,
            metadata=session.metadata
        )
    
    
    @app.get("/api/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str):
        """Get session information."""
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            user_id=session.user_id,
            project_name=session.project_name,
            status=session.status,
            metadata=session.metadata
        )
    
    
    @app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        """Delete a session."""
        success = await session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "success", "message": f"Session {session_id} deleted"}
    
    
    # Message endpoints
    @app.post("/api/sessions/{session_id}/messages", response_model=MessageResponse)
    async def send_message(session_id: str, request: MessageRequest):
        """Send a message in a session."""
        session = await session_manager.get_or_create_session(session_id)
        
        response = await session_manager.handle_message(session_id, request.text)
        
        # Create response
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Broadcast the message and response to websocket clients
        connection_manager = get_connection_manager()
        await connection_manager.broadcast(
            WebSocketMessage(
                type="message",
                content={
                    "id": message_id,
                    "text": request.text,
                    "sender": "user",
                    "timestamp": timestamp.isoformat()
                },
                session_id=session_id
            ),
            session_id
        )
        
        await connection_manager.broadcast(
            WebSocketMessage(
                type="message",
                content={
                    "id": str(uuid.uuid4()),
                    "text": response,
                    "sender": "assistant",
                    "timestamp": datetime.utcnow().isoformat()
                },
                session_id=session_id
            ),
            session_id
        )
        
        return MessageResponse(
            id=message_id,
            text=response,
            timestamp=timestamp,
            metadata={"session_id": session_id}
        )
    
    
    # Project analysis endpoints
    @app.post("/api/sessions/{session_id}/projects", response_model=WorkflowStatusResponse)
    async def start_project_analysis(session_id: str, request: ProjectAnalysisRequest):
        """Start a project analysis."""
        session = await session_manager.get_or_create_session(session_id)
        
        # Update session with project info
        session.project_name = request.project_name
        session.metadata["website"] = request.website
        session.metadata["github_url"] = request.github_url
        await session_manager.update_session(session)
        
        # Create workflow for project analysis
        from ..workflows.project_analysis_workflow import create_project_analysis_workflow
        
        workflow = create_project_analysis_workflow(
            project_name=request.project_name,
            website=request.website,
            github_url=request.github_url,
            ai_model_provider=AIModelProvider.GEMINI,  # Default to Gemini for better code analysis
            metadata=request.metadata
        )
        
        # Start the workflow
        workflow_id = await session_manager.start_workflow(session_id, workflow)
        if not workflow_id:
            raise HTTPException(status_code=500, detail="Failed to start workflow")
        
        # Return initial status
        return WorkflowStatusResponse(
            id=workflow_id,
            status="running",
            progress=0.0,
            tasks_total=len(workflow.tasks),
            tasks_completed=0,
            tasks_failed=0,
            started_at=datetime.utcnow(),
            metadata={"project_name": request.project_name}
        )
    
    
    @app.get("/api/sessions/{session_id}/workflows/current", response_model=Optional[WorkflowStatusResponse])
    async def get_current_workflow_status(session_id: str):
        """Get the status of the current workflow."""
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if not session.active_workflow:
            return None
        
        workflow = session.active_workflow
        completed_tasks = sum(1 for task in workflow.tasks.values() if task.is_completed())
        failed_tasks = sum(1 for task in workflow.tasks.values() if task.state == "failed")
        
        progress = 0.0
        if len(workflow.tasks) > 0:
            progress = completed_tasks / len(workflow.tasks)
        
        return WorkflowStatusResponse(
            id=workflow.id,
            status=workflow.state,
            progress=progress,
            tasks_total=len(workflow.tasks),
            tasks_completed=completed_tasks,
            tasks_failed=failed_tasks,
            started_at=workflow.started_at,
            metadata={"project_name": session.project_name}
        )
    
    
    # WebSocket endpoint
    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for real-time communication."""
        connection_manager = get_connection_manager()
        await connection_manager.connect(websocket, session_id)
        
        try:
            # Get or create the session
            session = await session_manager.get_or_create_session(session_id)
            
            # Send welcome message
            await connection_manager.send_message(
                websocket,
                WebSocketMessage(
                    type="welcome",
                    content=f"Connected to session {session_id}",
                    session_id=session_id
                )
            )
            
            # Process messages
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    await connection_manager.handle_client_message(websocket, message_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in WebSocket message: {data}")
                    await connection_manager.send_message(
                        websocket,
                        WebSocketMessage(
                            type="error",
                            content="Invalid JSON in message",
                            session_id=session_id
                        )
                    )
                except Exception as e:
                    logger.exception(f"Error handling WebSocket message: {str(e)}")
                    await connection_manager.send_message(
                        websocket,
                        WebSocketMessage(
                            type="error",
                            content=f"Error processing message: {str(e)}",
                            session_id=session_id
                        )
                    )
        except WebSocketDisconnect:
            await connection_manager.disconnect(websocket)
        except Exception as e:
            logger.exception(f"WebSocket error: {str(e)}")
            await connection_manager.disconnect(websocket)
    
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": session_manager.get_active_sessions_count(),
            "active_workflows": session_manager.get_active_workflows_count()
        }
    
    
    @app.get("/api/stats")
    async def get_stats():
        """Get system stats."""
        session_manager = get_session_manager()
        connection_manager = get_connection_manager()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": session_manager.get_active_sessions_count(),
            "active_workflows": session_manager.get_active_workflows_count(),
            "active_connections": connection_manager.get_connection_count()
        }
    
    return app


# For direct execution
app = create_app()


if __name__ == "__main__":
    # When run directly, start the server
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
