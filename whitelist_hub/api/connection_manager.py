"""Connection manager for WebSocket connections and project analysis sessions."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from ..models.message import MessageType, MessageStructure
from ..db.mongodb import get_collection, PROJECTS_COLLECTION

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and sessions."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket) -> bool:
        """Connect a new client.
        
        Args:
            session_id: Session identifier
            websocket: WebSocket connection
            
        Returns:
            Success status
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            # Initialize session data if not exists
            if session_id not in self.session_data:
                self.session_data[session_id] = {
                    "messages": [],
                    "created_at": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                    "project_data": None,
                    "analysis_status": "not_started"
                }
            logger.info(f"Client connected: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error connecting client {session_id}: {e}")
            return False
    
    def disconnect(self, session_id: str):
        """Disconnect a client.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Client disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to a client.
        
        Args:
            session_id: Session identifier
            message: Message to send
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Store message in session data
                if session_id in self.session_data:
                    if message.get("type") not in ["thinking", "system"]:
                        # Don't store system messages in history
                        if "messages" not in self.session_data[session_id]:
                            self.session_data[session_id]["messages"] = []
                        self.session_data[session_id]["messages"].append(message)
                    self.session_data[session_id]["last_active"] = datetime.now().isoformat()
                
                # Send message
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if exists, None otherwise
        """
        return self.session_data.get(session_id)
    
    def update_session_data(self, session_id: str, data: Dict[str, Any]):
        """Update session data.
        
        Args:
            session_id: Session identifier
            data: Data to update
        """
        if session_id in self.session_data:
            self.session_data[session_id].update(data)
            self.session_data[session_id]["last_active"] = datetime.now().isoformat()
    
    def update_project_data(self, session_id: str, project_data: Dict[str, Any]):
        """Update project data for a session.
        
        Args:
            session_id: Session identifier
            project_data: Project data
        """
        if session_id in self.session_data:
            self.session_data[session_id]["project_data"] = project_data
            self.session_data[session_id]["last_active"] = datetime.now().isoformat()
    
    def set_analysis_status(self, session_id: str, status: str):
        """Set analysis status for a session.
        
        Args:
            session_id: Session identifier
            status: Analysis status
        """
        if session_id in self.session_data:
            self.session_data[session_id]["analysis_status"] = status
            self.session_data[session_id]["last_active"] = datetime.now().isoformat()


class ProjectAnalysisManager(ConnectionManager):
    """Connection manager specialized for project analysis."""
    
    def __init__(self, db_client=None):
        """Initialize the project analysis manager.
        
        Args:
            db_client: Database client
        """
        super().__init__()
        self.db_client = db_client
    
    async def handle_client_message(self, session_id: str, data: str):
        """Handle client message for project analysis.
        
        Args:
            session_id: Session identifier
            data: Message data as string
        """
        try:
            # Parse message data
            message_data = json.loads(data)
            
            # Get message type and text
            message_type = message_data.get("type", "message")
            text = message_data.get("text", "")
            
            # Send acknowledgement
            await self.send_message(
                session_id,
                {
                    "type": "ack",
                    "message_id": message_data.get("id", str(uuid.uuid4())),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except json.JSONDecodeError:
            await self.send_message(
                session_id,
                MessageStructure.format_error("Invalid message format. Please send valid JSON.")
            )
        except Exception as e:
            logger.exception(f"Error handling client message: {e}")
            await self.send_message(
                session_id,
                MessageStructure.format_error(f"Error processing message: {str(e)}")
            )
    
    async def save_message(self, session_id: str, role: str, text: str):
        """Save message to session history.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            text: Message text
        """
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": text,
            "timestamp": datetime.now().isoformat()
        }
        
        if session_id in self.session_data:
            if "messages" not in self.session_data[session_id]:
                self.session_data[session_id]["messages"] = []
            
            self.session_data[session_id]["messages"].append(message)
        
        # If db_client is available, save to database
        if self.db_client:
            try:
                collection = await get_collection("messages")
                await collection.insert_one({
                    "session_id": session_id,
                    "message": message
                })
            except Exception as e:
                logger.error(f"Error saving message to database: {e}")
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages
        """
        if session_id in self.session_data and "messages" in self.session_data[session_id]:
            return self.session_data[session_id]["messages"]
        return []
    
    async def save_analysis_result(self, session_id: str, project_name: str, analysis_result: Dict[str, Any]):
        """Save analysis result to database and update session.
        
        Args:
            session_id: Session identifier
            project_name: Project name
            analysis_result: Analysis result
        """
        # Update session
        self.update_project_data(session_id, analysis_result)
        self.set_analysis_status(session_id, "completed")
        
        # Save to database if available
        if self.db_client:
            try:
                collection = await get_collection(PROJECTS_COLLECTION)
                await collection.update_one(
                    {"project_name": project_name.lower()},
                    {"$set": {
                        "project_name": project_name,
                        "analysis_result": analysis_result,
                        "last_updated": datetime.now().isoformat()
                    }},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error saving analysis result to database: {e}")
    
    async def broadcast_project_update(self, project_name: str, update_type: str, data: Dict[str, Any]):
        """Broadcast project update to all connected clients.
        
        Args:
            project_name: Project name
            update_type: Update type
            data: Update data
        """
        message = {
            "type": "project_update",
            "update_type": update_type,
            "project_name": project_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected clients
        for session_id in list(self.active_connections.keys()):
            session_data = self.get_session_data(session_id)
            if session_data and session_data.get("project_name") == project_name:
                await self.send_message(session_id, message)
    
    async def send_progress_update(self, session_id: str, stage: str, progress: float, message: str):
        """Send progress update for a long-running task.
        
        Args:
            session_id: Session identifier
            stage: Current analysis stage
            progress: Progress percentage (0-100)
            message: Progress message
        """
        progress_message = {
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_message(session_id, progress_message)
    
    async def report_analysis_step(self, session_id: str, step_name: str, step_number: int, total_steps: int):
        """Report analysis step progress.
        
        Args:
            session_id: Session identifier
            step_name: Step name
            step_number: Current step number
            total_steps: Total number of steps
        """
        progress = (step_number / total_steps) * 100
        
        await self.send_progress_update(
            session_id,
            stage="analysis",
            progress=progress,
            message=f"Step {step_number}/{total_steps}: {step_name}"
        )
    
    async def report_error(self, session_id: str, error_message: str):
        """Report error to client.
        
        Args:
            session_id: Session identifier
            error_message: Error message
        """
        await self.send_message(
            session_id,
            MessageStructure.format_error(error_message)
        )
        
        # Also update session status
        self.set_analysis_status(session_id, "error")
