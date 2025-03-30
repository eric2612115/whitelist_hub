"""
WebSocket connection manager for real-time communication.

This module provides a manager for WebSocket connections, allowing real-time
updates to be sent to connected clients during analysis sessions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..utils.observability import Observable

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Model for messages sent over WebSocket connections."""
    type: str
    content: Any
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConnectionManager(Observable):
    """Manager for WebSocket connections.
    
    This class maintains active WebSocket connections and provides methods
    for sending messages to connected clients.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        super().__init__()
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Connect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
            session_id: The session ID to associate with the connection
        """
        await websocket.accept()
        
        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            
            self.active_connections[session_id].append(websocket)
            self.connection_metadata[websocket] = {"session_id": session_id}
        
        logger.info(f"WebSocket client connected to session {session_id}")
        self.emit_event("websocket_connected", {"session_id": session_id})
        
        # Send initial connection acknowledgment
        await self.send_message(
            websocket,
            WebSocketMessage(
                type="connection_established",
                content=f"Connected to session {session_id}",
                session_id=session_id
            )
        )
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a WebSocket client.
        
        Args:
            websocket: The WebSocket connection
        """
        session_id = None
        
        async with self._lock:
            # Find and remove the connection
            for sid, connections in self.active_connections.items():
                if websocket in connections:
                    session_id = sid
                    connections.remove(websocket)
                    if not connections:
                        del self.active_connections[sid]
                    break
            
            # Remove metadata
            if websocket in self.connection_metadata:
                metadata = self.connection_metadata.pop(websocket)
                session_id = session_id or metadata.get("session_id")
        
        if session_id:
            logger.info(f"WebSocket client disconnected from session {session_id}")
            self.emit_event("websocket_disconnected", {"session_id": session_id})
    
    async def broadcast(self, message: WebSocketMessage, session_id: Optional[str] = None) -> None:
        """Broadcast a message to all connected clients for a session.
        
        Args:
            message: The message to broadcast
            session_id: The session ID to broadcast to, or None for all sessions
        """
        sessions_to_broadcast = [session_id] if session_id else list(self.active_connections.keys())
        
        for sid in sessions_to_broadcast:
            if sid in self.active_connections:
                message.session_id = sid
                await self.broadcast_to_session(message, sid)
    
    async def broadcast_to_session(self, message: WebSocketMessage, session_id: str) -> None:
        """Broadcast a message to all connected clients for a specific session.
        
        Args:
            message: The message to broadcast
            session_id: The session ID to broadcast to
        """
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
        
        # Make a copy of the connections list to avoid modification during iteration
        connections = []
        async with self._lock:
            connections = self.active_connections[session_id].copy()
        
        disconnected = []
        for websocket in connections:
            try:
                await self.send_message(websocket, message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {str(e)}")
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    if websocket in self.active_connections.get(session_id, []):
                        self.active_connections[session_id].remove(websocket)
                        logger.info(f"Removed disconnected WebSocket from session {session_id}")
                    
                    if websocket in self.connection_metadata:
                        del self.connection_metadata[websocket]
                
                # Remove empty sessions
                if session_id in self.active_connections and not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                    logger.info(f"Removed empty session {session_id}")
    
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """Send a message to a specific WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            message: The message to send
        """
        try:
            await websocket.send_text(message.json())
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {str(e)}")
            raise
    
    async def handle_client_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Handle a message from a client.
        
        Args:
            websocket: The WebSocket connection
            data: The message data
        """
        message_type = data.get("type", "unknown")
        content = data.get("content", "")
        
        # Get session ID from connection metadata
        session_id = None
        if websocket in self.connection_metadata:
            session_id = self.connection_metadata[websocket].get("session_id")
        
        if not session_id:
            # Try to extract from message
            session_id = data.get("session_id")
            if not session_id:
                logger.error("Received message without session ID")
                await self.send_message(
                    websocket,
                    WebSocketMessage(
                        type="error",
                        content="Message missing session ID"
                    )
                )
                return
        
        # Emit event for message received
        self.emit_event("websocket_message_received", {
            "session_id": session_id,
            "message_type": message_type,
            "content_length": len(str(content)) if content else 0
        })
        
        # Handle different message types
        if message_type == "ping":
            await self.send_message(
                websocket,
                WebSocketMessage(
                    type="pong",
                    content="pong",
                    session_id=session_id
                )
            )
        elif message_type == "message":
            # Forward to session manager
            from .session_manager import get_session_manager
            
            session_manager = get_session_manager()
            response = await session_manager.handle_message(session_id, content)
            
            await self.send_message(
                websocket,
                WebSocketMessage(
                    type="message",
                    content=response,
                    session_id=session_id
                )
            )
        else:
            # Unknown message type
            logger.warning(f"Unknown message type: {message_type}")
            await self.send_message(
                websocket,
                WebSocketMessage(
                    type="error",
                    content=f"Unknown message type: {message_type}",
                    session_id=session_id
                )
            )
    
    def get_active_sessions(self) -> List[str]:
        """Get the list of active sessions.
        
        Returns:
            List of session IDs with active connections
        """
        return list(self.active_connections.keys())
    
    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """Get the number of active connections.
        
        Args:
            session_id: Optional session ID to count connections for
            
        Returns:
            Number of active connections
        """
        if session_id:
            return len(self.active_connections.get(session_id, []))
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
_connection_manager = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance.
    
    Returns:
        The connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
