"""Connection manager for WebSocket connections and project analysis sessions."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from ..models.message import MessageType, MessageStructure

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and project analysis sessions."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_agents: Dict[str, Any] = {}
        self.busy_agents: Set[str] = set()
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
                    self.session_data[session_id]["messages"].append(message)
                    self.session_data[session_id]["last_active"] = datetime.now().isoformat()
                
                # Send message
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        for session_id in list(self.active_connections.keys()):
            await self.send_message(session_id, message)
    
    def set_agent_for_session(self, session_id: str, agent: Any):
        """Set agent for a session.
        
        Args:
            session_id: Session identifier
            agent: Agent instance
        """
        self.session_agents[session_id] = agent
    
    def get_agent_for_session(self, session_id: str) -> Optional[Any]:
        """Get agent for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Agent instance if exists, None otherwise
        """
        return self.session_agents.get(session_id)
    
    def is_agent_busy(self, session_id: str) -> bool:
        """Check if agent is busy.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if agent is busy, False otherwise
        """
        return session_id in self.busy_agents
    
    def set_agent_busy(self, session_id: str, busy: bool):
        """Set agent busy status.
        
        Args:
            session_id: Session identifier
            busy: Busy status
        """
        if busy:
            self.busy_agents.add(session_id)
        else:
            self.busy_agents.discard(session_id)
    
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
    
    async def handle_client_message(self, session_id: str, message_data: Dict[str, Any]):
        """Handle client message.
        
        Args:
            session_id: Session identifier
            message_data: Message data
        """
        # To be implemented by derived classes
        pass


class ProjectAnalysisManager(ConnectionManager):
    """Connection manager specialized for project analysis."""
    
    def __init__(self, db_client=None):
        """Initialize the project analysis manager.
        
        Args:
            db_client: Database client
        """
        super().__init__()
        self.db_client = db_client
        self.project_analyses: Dict[str, Dict[str, Any]] = {}
    
    async def handle_client_message(self, session_id: str, message_data: Dict[str, Any]):
        """Handle client message for project analysis.
        
        Args:
            session_id: Session identifier
            message_data: Message data
        """
        if self.is_agent_busy(session_id):
            await self.send_message(
                session_id,
                MessageStructure.format_error("Agent is busy processing another request")
            )
            return
        
        self.set_agent_busy(session_id, True)
        
        try:
            # Get message type and text
            message_type = message_data.get("type", "message")
            text = message_data.get("text", "")
            
            # Process message based on type
            if message_type == "start_analysis":
                # Start new project analysis
                project_name = message_data.get("project_name", "")
                website = message_data.get("website", "")
                github_url = message_data.get("github_url", "")
                
                await self.start_project_analysis(session_id, project_name, website, github_url)
            
            elif message_type == "message":
                # Process regular message
                if not text:
                    await self.send_message(
                        session_id,
                        MessageStructure.format_error("Message text is required")
                    )
                    return
                
                # Save message
                await self.save_message(session_id, "user", text)
                
                # Process message with agent
                agent = self.get_agent_for_session(session_id)
                if not agent:
                    await self.send_message(
                        session_id,
                        MessageStructure.format_error("No agent assigned to this session")
                    )
                    return
                
                # Process message with agent
                response = await self.process_message_with_agent(session_id, agent, text)
                
                # Save response
                await self.save_message(session_id, "assistant", response)
                
                # Send response
                await self.send_message(
                    session_id,
                    MessageStructure.format_ai_response(response)
                )
            
            elif message_type == "get_analysis_status":
                # Get analysis status
                status = self.get_session_data(session_id).get("analysis_status", "not_started")
                project_data = self.get_session_data(session_id).get("project_data")
                
                await self.send_message(
                    session_id,
                    {
                        "type": "analysis_status",
                        "status": status,
                        "project_data": project_data
                    }
                )
        
        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            await self.send_message(
                session_id,
                MessageStructure.format_error(f"Error processing message: {str(e)}")
            )
        
        finally:
            self.set_agent_busy(session_id, False)
    
    async def start_project_analysis(self, session_id: str, project_name: str, website: str, github_url: str):
        """Start a new project analysis.
        
        Args:
            session_id: Session identifier
            project_name: Project name
            website: Project website
            github_url: Project GitHub URL
        """
        # Update session data
        self.update_session_data(session_id, {
            "project_name": project_name,
            "website": website,
            "github_url": github_url,
            "analysis_status": "in_progress"
        })
        
        # Send acknowledgement
        await self.send_message(
            session_id,
            {
                "type": "analysis_started",
                "project_name": project_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # TODO: Implement actual analysis logic with agent
        # This would be a good place to use the Agent framework
    
    async def process_message_with_agent(self, session_id: str, agent: Any, text: str) -> str:
        """Process message with agent.
        
        Args:
            session_id: Session identifier
            agent: Agent instance
            text: Message text
            
        Returns:
            Agent response
        """
        # Send thinking status
        await self.send_message(
            session_id,
            MessageStructure.format_thinking()
        )
        
        # TODO: Implement actual message processing with agent
        # For now, return a placeholder response
        await asyncio.sleep(1)  # Simulate processing time
        
        return f"I'm processing your message about: {text}"
    
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
            # TODO: Implement database saving
            pass
    
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
    
    def get_project_analysis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get project analysis result.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Project analysis result if available
        """
        return self.project_analyses.get(session_id)
    
    def store_project_analysis(self, session_id: str, analysis: Dict[str, Any]):
        """Store project analysis result.
        
        Args:
            session_id: Session identifier
            analysis: Analysis result
        """
        self.project_analyses[session_id] = analysis
        self.update_session_data(session_id, {
            "analysis_status": "completed",
            "completed_at": datetime.now().isoformat()
        })
