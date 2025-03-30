"""
Session manager for handling analysis sessions.

This module provides a manager for analysis sessions, allowing multiple
concurrent analysis workflows to be executed and tracked.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field

from ..utils.observability import Observable
from ..agent_framework.context import Context
from ..agent_framework.workflow import Workflow, WorkflowConfig

logger = logging.getLogger(__name__)


class Session(BaseModel):
    """Model for an analysis session."""
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    project_name: Optional[str] = None
    status: str = "active"
    contexts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    current_context_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    # Runtime properties (not serialized)
    active_workflow: Optional[Workflow] = None
    workflow_task = None


class SessionManager(Observable):
    """Manager for analysis sessions.
    
    This class maintains active analysis sessions and provides methods
    for creating, retrieving, and managing them.
    """
    
    def __init__(self, db_client=None):
        """Initialize the session manager.
        
        Args:
            db_client: Optional database client for persistence
        """
        super().__init__()
        self.sessions: Dict[str, Session] = {}
        self.db_client = db_client
        self._lock = asyncio.Lock()
    
    async def create_session(self, user_id: Optional[str] = None) -> Session:
        """Create a new analysis session.
        
        Args:
            user_id: Optional user ID to associate with the session
            
        Returns:
            The created session
        """
        session_id = str(uuid.uuid4())
        
        session = Session(
            id=session_id,
            user_id=user_id,
            status="active"
        )
        
        # Create an initial context
        context = Context(session_id=session_id)
        session.contexts[context.id] = context.dict()
        session.current_context_id = context.id
        
        async with self._lock:
            self.sessions[session_id] = session
        
        # Store in database if available
        if self.db_client:
            await self.db_client.sessions.insert_one(session.dict(exclude={"active_workflow", "workflow_task"}))
        
        logger.info(f"Created new session: {session_id}")
        self.emit_event("session_created", {"session_id": session_id})
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session, or None if not found
        """
        # Check in-memory cache
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try to load from database
        if self.db_client:
            session_data = await self.db_client.sessions.find_one({"id": session_id})
            if session_data:
                session = Session(**session_data)
                async with self._lock:
                    self.sessions[session_id] = session
                return session
        
        return None
    
    async def update_session(self, session: Session) -> None:
        """Update a session.
        
        Args:
            session: The session to update
        """
        session.updated_at = datetime.utcnow()
        
        async with self._lock:
            self.sessions[session.id] = session
        
        # Update in database if available
        if self.db_client:
            await self.db_client.sessions.update_one(
                {"id": session.id},
                {"$set": session.dict(exclude={"active_workflow", "workflow_task"})}
            )
        
        logger.debug(f"Updated session: {session.id}")
        self.emit_event("session_updated", {"session_id": session.id})
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if the session was deleted, False otherwise
        """
        if session_id not in self.sessions:
            return False
        
        # Cancel any active workflow
        session = self.sessions[session_id]
        if session.active_workflow:
            session.active_workflow.cancel()
            if session.workflow_task and not session.workflow_task.done():
                session.workflow_task.cancel()
                try:
                    await session.workflow_task
                except asyncio.CancelledError:
                    pass
        
        # Remove from in-memory cache
        async with self._lock:
            del self.sessions[session_id]
        
        # Remove from database if available
        if self.db_client:
            await self.db_client.sessions.delete_one({"id": session_id})
        
        logger.info(f"Deleted session: {session_id}")
        self.emit_event("session_deleted", {"session_id": session_id})
        
        return True
    
    async def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> Session:
        """Get an existing session or create a new one.
        
        Args:
            session_id: Optional existing session ID
            user_id: Optional user ID for a new session
            
        Returns:
            The session (existing or newly created)
        """
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
        
        # Create a new session
        return await self.create_session(user_id)
    
    async def get_current_context(self, session_id: str) -> Optional[Context]:
        """Get the current context for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The current context, or None if not found
        """
        session = await self.get_session(session_id)
        if not session or not session.current_context_id:
            return None
        
        context_data = session.contexts.get(session.current_context_id)
        if not context_data:
            return None
        
        return Context(**context_data)
    
    async def add_context(self, session_id: str, context: Context) -> bool:
        """Add a context to a session.
        
        Args:
            session_id: The session ID
            context: The context to add
            
        Returns:
            True if the context was added, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        
        # Ensure session ID is set
        context.session_id = session_id
        
        # Add to session
        session.contexts[context.id] = context.dict()
        session.current_context_id = context.id
        
        # Update session
        await self.update_session(session)
        
        logger.debug(f"Added context {context.id} to session {session_id}")
        self.emit_event("context_added", {
            "session_id": session_id,
            "context_id": context.id
        })
        
        return True
    
    async def update_context(self, session_id: str, context: Context) -> bool:
        """Update a context in a session.
        
        Args:
            session_id: The session ID
            context: The context to update
            
        Returns:
            True if the context was updated, False otherwise
        """
        session = await self.get_session(session_id)
        if not session or context.id not in session.contexts:
            return False
        
        # Update in session
        session.contexts[context.id] = context.dict()
        
        # Update session
        await self.update_session(session)
        
        logger.debug(f"Updated context {context.id} in session {session_id}")
        self.emit_event("context_updated", {
            "session_id": session_id,
            "context_id": context.id
        })
        
        return True
    
    async def start_workflow(self, session_id: str, workflow: Workflow) -> Optional[str]:
        """Start a workflow in a session.
        
        Args:
            session_id: The session ID
            workflow: The workflow to start
            
        Returns:
            The workflow ID if started successfully, None otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Cancel any existing workflow
        if session.active_workflow:
            session.active_workflow.cancel()
            if session.workflow_task and not session.workflow_task.done():
                session.workflow_task.cancel()
                try:
                    await session.workflow_task
                except asyncio.CancelledError:
                    pass
        
        # Get the current context
        context = await self.get_current_context(session_id)
        if not context:
            context = Context(session_id=session_id)
            await self.add_context(session_id, context)
        
        # Set workflow session ID
        workflow.session_id = session_id
        
        # Add workflow to session
        session.active_workflow = workflow
        
        # Create task to run workflow
        async def run_workflow_task():
            try:
                # Add event listeners for workflow
                connection_manager = None
                try:
                    from .connection_manager import get_connection_manager
                    connection_manager = get_connection_manager()
                    
                    # Forward workflow events to WebSocket clients
                    def workflow_event_handler(event: str, data: Dict[str, Any]):
                        if connection_manager:
                            from .connection_manager import WebSocketMessage
                            
                            asyncio.create_task(connection_manager.broadcast(
                                WebSocketMessage(
                                    type=f"workflow_{event}",
                                    content=data,
                                    session_id=session_id
                                ),
                                session_id
                            ))
                    
                    workflow.add_global_listener(workflow_event_handler)
                except ImportError:
                    pass
                
                # Execute workflow
                result_context = await workflow.execute(context)
                
                # Update context with results
                await self.update_context(session_id, result_context)
                
                # Notify completion
                self.emit_event("workflow_completed", {
                    "session_id": session_id,
                    "workflow_id": workflow.id
                })
                
                # Notify clients if connection manager is available
                if connection_manager:
                    from .connection_manager import WebSocketMessage
                    
                    asyncio.create_task(connection_manager.broadcast(
                        WebSocketMessage(
                            type="workflow_completed",
                            content={
                                "workflow_id": workflow.id,
                                "execution_time": (
                                    workflow.completed_at - workflow.started_at
                                ).total_seconds() if workflow.completed_at and workflow.started_at else None,
                                "outputs": result_context.outputs
                            },
                            session_id=session_id
                        ),
                        session_id
                    ))
                
                # Clear active workflow
                session.active_workflow = None
                session.workflow_task = None
                await self.update_session(session)
                
                return result_context
                
            except asyncio.CancelledError:
                logger.info(f"Workflow {workflow.id} cancelled")
                # Notify cancellation
                self.emit_event("workflow_cancelled", {
                    "session_id": session_id,
                    "workflow_id": workflow.id
                })
                
                # Clear active workflow
                session.active_workflow = None
                session.workflow_task = None
                await self.update_session(session)
                
                raise
                
            except Exception as e:
                logger.exception(f"Error in workflow {workflow.id}: {str(e)}")
                # Notify error
                self.emit_event("workflow_error", {
                    "session_id": session_id,
                    "workflow_id": workflow.id,
                    "error": str(e)
                })
                
                # Clear active workflow
                session.active_workflow = None
                session.workflow_task = None
                await self.update_session(session)
                
                raise
        
        # Start the workflow task
        session.workflow_task = asyncio.create_task(run_workflow_task())
        
        # Update session
        await self.update_session(session)
        
        logger.info(f"Started workflow {workflow.id} in session {session_id}")
        self.emit_event("workflow_started", {
            "session_id": session_id,
            "workflow_id": workflow.id
        })
        
        return workflow.id
    
    async def handle_message(self, session_id: str, message: str) -> str:
        """Handle a message from a client.
        
        Args:
            session_id: The session ID
            message: The message text
            
        Returns:
            The response message
        """
        # Get or create the session
        session = await self.get_or_create_session(session_id)
        
        # Get the current context
        context = await self.get_current_context(session_id)
        if not context:
            context = Context(session_id=session_id)
            await self.add_context(session_id, context)
        
        # Add the user message to the context
        context.add_user_message(message)
        await self.update_context(session_id, context)
        
        # Process the message
        response = await self._process_message(session, context, message)
        
        # Add the assistant message to the context
        context.add_assistant_message(response)
        await self.update_context(session_id, context)
        
        return response
    
    async def _process_message(self, session: Session, context: Context, message: str) -> str:
        """Process a message from a client.
        
        Args:
            session: The session
            context: The context
            message: The message text
            
        Returns:
            The response message
        """
        # If a workflow is active, return status
        if session.active_workflow:
            return (
                f"A workflow is currently running in this session. "
                f"Please wait for it to complete before sending more messages."
            )
        
        # TODO: Add message processing logic
        # For now, just return a simple response
        return f"Received your message: {message}"
    
    def get_active_sessions_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.sessions)
    
    def get_active_workflows_count(self) -> int:
        """Get the number of active workflows.
        
        Returns:
            Number of active workflows
        """
        return sum(1 for session in self.sessions.values() if session.active_workflow)


# Global session manager instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.
    
    Returns:
        The session manager
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
